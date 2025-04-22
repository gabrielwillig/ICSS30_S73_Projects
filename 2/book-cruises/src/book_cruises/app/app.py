import json
from flask import Flask, render_template, request
from book_cruises.commons.utils import logger
from book_cruises.commons.utils import config, RabbitMQProducer
from .di import config_dependencies, get_rabbitmq_producer

import time

# Initialize Flask app
app = Flask(__name__)
flask_configs = {
    "debug": config.DEBUG,
    "host": config.HOST,
    "port": config.PORT,
    "user_reloader": config.DEBUG,
}
app.config.from_mapping(flask_configs)

# Get RabbitMQ middleware
config_dependencies()
producer: RabbitMQProducer = get_rabbitmq_producer()



@app.route("/", methods=["GET", "POST"])
def index():
    trips = []
    if request.method == "POST":
        query_message = {
            "departure_date": request.form.get("departure_date"),
            "departure_harbor": request.form.get("departure_harbor"),
            "arrival_harbor": request.form.get("arrival_harbor"),
        }

        # Create a temporary queue for the response
        try:
            trips = producer.rpc_publish(
                config.BOOK_SVC_QUEUE,
                query_message,
                timeout=5,
            )
        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    return render_template("index.html", trips=trips)


@app.route("/payment", methods=["POST"])
def payment():
    try:
        trip_id = request.form.get("trip_id")
        price = request.form.get("price")

        # Simulate payment processing (you can integrate with a payment gateway here)
        logger.info(f"Processing payment for trip ID {trip_id} with price ${price}")

        raise NotImplementedError

        # Return a success message or redirect to a confirmation page
        return render_template("payment_success.html", trip_id=trip_id, price=price)
    except Exception as e:
        logger.error(f"Failed to process payment: {e}")
        return "An error occurred while processing the payment.", 500


def main():
    logger.info("Starting Flask app...")
    app.run()
