import json
import random
import time
import threading
import requests
import uuid
from flask import Flask, render_template, request, session, jsonify, Response, stream_with_context
from book_cruises.commons.utils import config, logger
from book_cruises.commons.domains import Payment, Itinerary
from book_cruises.commons.messaging import Producer, Consumer
from .di import configure_dependencies, get_producer, get_consumer
from pika.exceptions import ChannelWrongStateError

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "sistemas-distribuidos"  # Add a secret key for sessions

configure_dependencies()
producer: Producer = get_producer()
consumer: Consumer = get_consumer()

# Simple in-memory payment tracking
payment_statuses = {}


def process_payment_after_delay(payment_info: Payment):
    """Background task to process payment after a delay"""
    logger.debug(payment_info)
    payment_id = payment_info.get("payment_id")
    logger.info(f"Started payment processing for {payment_id}")

    # Sleep for 5-10 seconds to simulate payment processing
    time.sleep(random.uniform(5, 10))

    try:
        # Make API call to create reservation
        response = requests.post(
            f"http://{config.BOOK_SVC_WEB_SERVER_HOST}:{config.BOOK_SVC_WEB_SERVER_PORT}/create_reservation", json=payment_info, timeout=10
        )

        if response.status_code == 200:
            logger.info(f"Reservation created successfully for payment {payment_id}")
            # Update payment status to "success"
            payment_statuses[payment_id] = "success"
        else:
            logger.error(f"Failed to create reservation: {response.text}")
            # You might want to update payment status or add an error flag
            payment_statuses[payment_id] = "error"

    except Exception as e:
        logger.error(f"Error calling reservation service: {e}")
        payment_statuses[payment_id] = "error"


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
        # Generate a unique payment ID
        payment_id = f"{trip_id}-{int(time.time())}"

        payment_obj = Payment(
            payment_id=payment_id, trip_id=trip_id, price=price, passengers=passengers
        )

        session["payment_info"] = payment_obj.dict()
        session["payment_id"] = payment_id

        # Set initial payment status to "processing"
        payment_statuses[payment_id] = payment_obj.status

        # Log payment process start
        logger.info(
            f"Started payment process ID {payment_id} with price ${price} for {passengers} passengers"
        )

        # Start background thread to process payment after delay
        payment_thread = threading.Thread(
            target=process_payment_after_delay,
            args=(payment_obj.dict(),),
            daemon=True,
        )
        payment_thread.start()

        # Return the payment processing page with initial "processing" status
        return render_template(
            "payment.html",
            price=price,
            payment_id=payment_id,
            passengers=passengers,
            payment_status=payment_obj.status,
        )
    except Exception as e:
        logger.error(f"Failed to process payment: {e}")
        return "An error occurred while processing the payment.", 500


@app.route("/payment/status", methods=["GET"])
def payment_status():
    """Endpoint to check the current payment status"""
    payment_id = session.get("payment_id")

    if not payment_id or payment_id not in payment_statuses:
        return jsonify({"status": "unknown"})
    return jsonify({"status": payment_statuses[payment_id]})


@app.route("/ticket", methods=["GET"])
def ticket():
    try:
        trip_id = session.get("payment_id")
        return render_template("ticket.html", trip_id=trip_id)
    except Exception as e:
        logger.error(f"Failed to display ticket: {e}")
        return render_template("error.html", message="Unable to display your ticket."), 500

@app.route('/subscribe/<destination>')
def subscribe_to_promotions(destination):
    """Subscribe to promotions for a specific destination using Server-Sent Events"""
    def generate():

        routing_key = destination.lower().replace(" ", "_")
        # Normalize destination name

        consumer_id = uuid.uuid4().hex

        queue_name = f"{routing_key}_consumer_{consumer_id}"

        consumer.exchange_declare(config.PROMOTIONS_EXCHANGE, exchange_type="topic")

        consumer.queue_declare(queue_name)

        consumer.queue_bind(queue_name, config.PROMOTIONS_EXCHANGE, routing_key)
        
        logger.info(f"Client {consumer_id} subscribed to promotions for {destination}")
        
        try:
            while True:
                method, props, body = consumer.basic_consume(queue_name)
                if method:
                    logger.info(f"Sending promotion to {destination} for client {consumer_id}")
                    yield f"data: {body.decode()}\n\n"
                    consumer.channel.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    time.sleep(1)  # No message, wait a bit before checking again
                
        except (GeneratorExit, ChannelWrongStateError):
            logger.info(f"Client unsubscribed from {destination} promotions")
        except Exception as e:
            logger.error(f"Error in promotion stream for {destination}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            consumer.delete_queue(queue_name)
            consumer.close()
            logger.info(f"Closed connection for {destination} promotion subscriber {consumer_id}")

    # Use Flask's streaming response with correct SSE headers
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Helps with certain proxies
        }
    )

def main():
    logger.info("Starting Flask app...")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
