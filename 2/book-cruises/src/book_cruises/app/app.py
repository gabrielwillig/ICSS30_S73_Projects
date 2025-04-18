import json
import uuid
from flask import Flask, render_template, request
from book_cruises.commons.utils import logger
from book_cruises.commons.utils import config
from .di import initialize_dependencies, get_message_middleware

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
initialize_dependencies()
msg_middleware = get_message_middleware()

response_storage = {}  # Store responses temporarily


def process_response(message):
    """Callback to process responses from RabbitMQ."""
    try:
        response = json.loads(message)
        logger.info(f"Received response: {response}")

        # Store the response in the temporary storage
        response_id = response.get("id")
        if response_id:
            response_storage[response_id] = response
            logger.info(f"Stored response with ID {response_id}")
    except Exception as e:
        logger.error(f"Failed to process message: {e}")


@app.route("/", methods=["GET", "POST"])
def index():
    trips = []
    if request.method == "POST":
        correlation_id = str(uuid.uuid4())
        query_message = {
            "departure_date": request.form.get("departure_date"),
            "departure_harbor": request.form.get("departure_harbor"),
            "arrival_harbor": request.form.get("arrival_harbor"),
        }
        msg_middleware.publish_message(
            config.BOOK_SVC_QUEUE,
            json.dumps(query_message),
            properties={"correlation_id": correlation_id},
        )

    return render_template("index.html", trips=trips)


def main():
    logger.info("Starting Flask app...")
    app.run()
