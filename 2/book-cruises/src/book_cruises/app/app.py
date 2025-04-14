import inject
import json
import uuid
from flask import Flask, render_template, request
from book_cruises.commons.utils import MessageMiddleware
from book_cruises.commons.utils import logger
from book_cruises.commons.utils import config
from .di import configure_dependencies

# Initialize Flask app
app = Flask(__name__)
flask_configs = {
    "debug": config.DEBUG,
    "host": config.HOST,
    "port": config.PORT,
    "user_reloader": config.DEBUG,
}
app.config.from_mapping(flask_configs)

# Initialize Middleware
inject.configure(configure_dependencies)  # Initialize the DI container
msg_middleware = inject.instance(MessageMiddleware)

response_storage = {}  # Store responses temporarily

def process_response(message):
    """Callback to process responses from RabbitMQ."""
    try:
        response = json.loads(message)
        correlation_id = response.get("correlation_id")
        if correlation_id and correlation_id in response_storage:
            response_storage[correlation_id] = response.get("trips", [])
    except Exception as e:
        logger.error(f"Failed to process response: {e}")


@app.route("/", methods=["GET", "POST"])
def index():
    trips = []
    if request.method == "POST":
        destination = request.form.get("destination")
        correlation_id = str(uuid.uuid4())  # Generate a unique correlation ID

        # Publish the query message
        query_message = {
            "action": "get_trips",
            "destination": destination,
            "correlation_id": correlation_id
        }
        msg_middleware.publish_message(json.dumps(query_message))

        # Wait for the response (simulate synchronous behavior)
        response_storage[correlation_id] = None
        for _ in range(10):  # Retry for a few seconds
            if response_storage[correlation_id] is not None:
                trips = response_storage.pop(correlation_id)
                break

    return render_template("index.html", trips=trips)

def main():
    logger.info("Starting Flask app...")
    app.run()  
