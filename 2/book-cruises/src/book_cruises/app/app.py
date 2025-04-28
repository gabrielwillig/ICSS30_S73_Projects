import json
import random
import time
import requests
import uuid
from flask import Flask, render_template, request, session, jsonify, Response, stream_with_context
from book_cruises.commons.utils import config, logger
from book_cruises.commons.domains import Payment, Itinerary
from book_cruises.commons.messaging import Producer, Consumer
from .di import configure_dependencies, get_producer, get_consumer

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "sistemas-distribuidos"  # Add a secret key for sessions

configure_dependencies()
producer: Producer = get_producer()
consumer: Consumer = get_consumer()


@app.route("/", methods=["GET", "POST"])
def index():
    trips = []
    if request.method == "POST":
        query_message = {
            "departure_date": request.form.get("departure_date"),
            "departure_harbor": request.form.get("departure_harbor"),
            "arrival_harbor": request.form.get("arrival_harbor"),
        }

        try:
            trips = producer.rpc_publish(
                config.QUERY_RESERVATION_QUEUE,
                query_message,
                timeout=5,
            )
            logger.info(f"Received trips: {trips}")
        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    return render_template("index.html", trips=trips)


@app.route("/book", methods=["POST"])
def book():
    try:
        trip_id = request.form.get("trip_id")
        price = request.form.get("price")

        # Use a default date or get it from the form if available
        departure_date = request.form.get("departure_date", "2026-01-01")

        # Instead of raising NotImplementedError, render the booking form
        logger.info(f"Showing booking form for trip ID {trip_id} with base price ${price}")

        return render_template(
            "book.html", trip_id=trip_id, price=price, departure_date=departure_date
        )
    except Exception as e:
        logger.error(f"Failed to process payment: {e}")
        return "An error occurred while processing your request.", 500


@app.route("/payment", methods=["POST"])
def payment():
    try:
        trip_id = request.form.get("trip_id")
        price = float(request.form.get("price"))
        passengers = int(request.form.get("passengers", 1))
        payment_id = f"{trip_id}-{int(time.time())}"

        payment_obj = Payment(
            payment_id=payment_id, trip_id=trip_id, price=price, passengers=passengers
        )
        payment_info = payment_obj.dict()

        # Make API call to create reservation
        response = requests.post(
            f"http://{config.BOOK_SVC_WEB_SERVER_HOST}:{config.BOOK_SVC_WEB_SERVER_PORT}/create_reservation",
            json=payment_info,
            timeout=10,
        )

        reservation_id = response.json().get("reservation_id")

        session["payment_info"] = payment_info
        session["payment_id"] = payment_id
        session["reservation_id"] = reservation_id
        session["payment_status"] = "processing"
        session["ticket_status"] = "processing"

        # Log payment process start
        logger.info(
            f"Started payment process ID {payment_id} of reservation_id {reservation_id} with price ${price} for {passengers} passengers"
        )

        # Return the payment processing page with initial "processing" status
        return render_template(
            "payment.html",
            price=price,
            payment_id=payment_id,
            passengers=passengers,
            payment_status=payment_obj.status,
        )
    except Exception as e:
        logger.error(f"Failed to process payment: {e.with_traceback()}")
        return "An error occurred while processing the payment.", 500


@app.route("/payment/status", methods=["GET"])
def payment_status():
    """Endpoint to check the current payment status"""
    reservation_id = session.get("reservation_id")
    if not reservation_id:
        return jsonify({"status": "error", "message": "No reservation ID in session"}), 400

    try:
        response = requests.get(
            f"http://{config.BOOK_SVC_WEB_SERVER_HOST}:{config.BOOK_SVC_WEB_SERVER_PORT}/payment/status",
            params={"reservation_id": reservation_id},
            timeout=5,
        )
        payment_status = response.json().get("status")
        logger.info(f"Payment status for {reservation_id}: {payment_status}")

        if payment_status in ["approved", "refused"]:
            session["payment_status"] = payment_status
            return jsonify({"status": payment_status}), 200
    except requests.RequestException as e:
        logger.error(f"Error checking payment status: {e}")
    time.sleep(1)


@app.route("/ticket", methods=["GET"])
def ticket():
    """Render the ticket page to wait for ticket generation"""
    reservation_id = session.get("reservation_id")
    if not reservation_id:
        return jsonify({"status": "error", "message": "No reservation ID in session"}), 400

    # Render the ticket.html template, which will handle polling for ticket status
    return render_template("ticket.html")


@app.route("/ticket/status", methods=["GET"])
def ticket_status():
    """Endpoint to check the ticket generation status and render the result"""
    reservation_id = session.get("reservation_id")
    if not reservation_id:
        return jsonify({"status": "error", "message": "No reservation ID in session"}), 400

    try:
        response = requests.get(
            f"http://{config.BOOK_SVC_WEB_SERVER_HOST}:{config.BOOK_SVC_WEB_SERVER_PORT}/ticket/status",
            params={"reservation_id": reservation_id},
            timeout=5,
        )
        ticket_status = response.json().get("status")
        logger.info(f"Ticket status for {reservation_id}: {ticket_status}")

        if ticket_status == "ticket_generated":
            session["ticket_status"] = ticket_status
            return jsonify({"status": "ticket_generated"}), 200

        elif ticket_status == "error":
            return jsonify({"status": "error", "message": "Error in generating ticket"}), 500

    except requests.RequestException as e:
        logger.error(f"Error checking ticket status: {e}")
        return jsonify({"status": "error", "message": "Unable to check ticket status."}), 500


@app.route("/subscribe/<destination>")
def subscribe_to_promotions(destination):
    """Subscribe to promotions for a specific destination using Server-Sent Events"""

    def generate():
        # Normalize destination name
        queue_name = f"{destination.lower()}_consumer_{uuid.uuid4().hex}"

        exchange_name = f"{destination.lower()}_promotions_exchange"

        consumer.exchange_declare(exchange_name, exchange_type="fanout")

        consumer.queue_declare(queue_name)

        consumer.queue_bind(queue_name, exchange_name)

        logger.info(f"Client subscribed to promotions for {destination}")

        try:
            while True:
                method, props, body = consumer.basic_consume(queue_name)
                if method:
                    logger.info(f"Sending promotion to {destination}")
                    yield f"data: {body.decode()}\n\n"
                    consumer.channel.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    time.sleep(1)  # No message, wait a bit before checking again

        except GeneratorExit:
            logger.info(f"Client unsubscribed from {destination} promotions")
        except Exception as e:
            logger.error(f"Error in promotion stream for {destination}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            consumer.close()
            consumer.delete_queue(queue_name)
            logger.info(f"Closed connection for {destination} promotion subscriber")

    # Use Flask's streaming response with correct SSE headers
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Helps with certain proxies
        },
    )


def main():
    logger.info("Starting Flask app...")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
