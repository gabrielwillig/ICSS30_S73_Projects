import json
from flask import Flask, render_template, request
from book_cruises.commons.utils import logger
from book_cruises.commons.utils import config
from .di import config_dependencies, get_message_middleware

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
msg_middleware = get_message_middleware()


def process_response(message, properties):
    """Callback to process responses from RabbitMQ."""
    try:
        response = json.loads(message)
        logger.info(f"Received response: {response}")

        # Store the response in the temporary storage
        correlation_id = properties.correlation_id
        if correlation_id:
            msg_middleware.set_response_storage(correlation_id, response)
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
    logger.info(f"Received response: {message}")


@app.route("/", methods=["GET", "POST"])
def index():
    trips = []
    if request.method == "POST":
        query_message = {
            "departure_date": request.form.get("departure_date"),
            "departure_harbor": request.form.get("departure_harbor"),
            "arrival_harbor": request.form.get("arrival_harbor"),
        }

        if not msg_middleware.is_connected():
            msg_middleware.initialize()

        # Create a temporary queue for the response
        try:
            trips = msg_middleware.publish_consume(
                config.BOOK_SVC_QUEUE,
                query_message,
                process_response,
            )
        except Exception as e:
            logger.error(f"Failed to process message: {e}")

    return render_template("index.html", trips=trips)


def main():
    logger.info("Starting Flask app...")
    app.run()
