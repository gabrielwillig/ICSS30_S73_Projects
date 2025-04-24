import json
import random
import time
import threading
import requests
from flask import Flask, render_template, request, session, jsonify
from book_cruises.commons.utils import config, logger
from book_cruises.commons.domains import Payment, Itinerary
from book_cruises.commons.messaging import Producer
from .di import configure_dependencies, get_producer

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "sistemas-distribuidos"  # Add a secret key for sessions
flask_configs = {
    "debug": config.DEBUG,
    "host": config.HOST,
    "port": config.PORT,
    "user_reloader": config.DEBUG,
}
app.config.from_mapping(flask_configs)

configure_dependencies()
producer: Producer = get_producer()

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
            "http://127.0.0.1:5001/create_reservation", json=payment_info, timeout=10
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
        trip_id = request.args.get("trip_id")
        # In a real application, you would verify the ticket exists and is valid

        # For now, just return a simple message
        return f"<h1>Ticket for Trip {trip_id}</h1><p>Your ticket has been issued successfully!</p><a href='/'>Return Home</a>"
    except Exception as e:
        logger.error(f"Failed to display ticket: {e}")
        return "An error occurred while displaying your ticket.", 500


def main():
    logger.info("Starting Flask app...")
    app.run()
