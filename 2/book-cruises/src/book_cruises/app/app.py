import json
from flask import Flask, render_template, request
from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Producer
from .di import configure_dependencies, get_producer

# Initialize Flask app
app = Flask(__name__)
flask_configs = {
    "debug": config.DEBUG,
    "host": config.HOST,
    "port": config.PORT,
    "user_reloader": config.DEBUG,
}
app.config.from_mapping(flask_configs)

configure_dependencies()
producer: Producer = get_producer()


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
                config.BOOK_SVC_QUEUE,
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
        
        return render_template("book.html", trip_id=trip_id, price=price, departure_date=departure_date)
    except Exception as e:
        logger.error(f"Failed to process payment: {e}")
        return "An error occurred while processing your request.", 500

@app.route("/payment", methods=["POST"])
def payment():
    try:
        trip_id = request.form.get("trip_id")
        price = request.form.get("price")

        # Simulate payment processing (you can integrate with a payment gateway here)
        logger.info(f"Processing payment for trip ID {trip_id} with price ${price}")

        raise NotImplementedError

        # Return a success message or redirect to a confirmation page
        return render_template("payment.html", trip_id=trip_id, price=price)
    except Exception as e:
        logger.error(f"Failed to process payment: {e}")
        return "An error occurred while processing the payment.", 500

def main():
    logger.info("Starting Flask app...")
    app.run()
