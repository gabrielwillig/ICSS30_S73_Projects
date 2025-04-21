import json
import uuid
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

response_storage = {}  # Store responses temporarily


def process_response(message, test):
    """Callback to process responses from RabbitMQ."""
    # try:
    #     response = json.loads(message)
    #     logger.info(f"Received response: {response}")

    #     # Store the response in the temporary storage
    #     response_id = response.get("id")
    #     if response_id:
    #         response_storage[response_id] = response
    #         logger.info(f"Stored response with ID {response_id}")
    # except Exception as e:
    #     logger.error(f"Failed to process message: {e}")
    logger.info(f"Received response: {message}")


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

        if not msg_middleware.is_connected():
            msg_middleware.initialize()
            
        # Create a temporary queue for the response
        try:
            # Create response queue and set callback
            response_queue_name = f"book-svc-response-queue-{correlation_id}"
            response_queue_id = msg_middleware.create_temporary_queue(response_queue_name)
            msg_middleware.consume_messages({response_queue_id: process_response})
            
            # Send message
            msg_middleware.publish_message(
                config.BOOK_SVC_QUEUE,
                json.dumps(query_message),
                properties={"correlation_id": correlation_id, "reply_to": response_queue_id},
            )
            
            # Modified part: consume for a limited time
            timeout = time.time() + 5  # 5-second timeout
            
            while time.time() < timeout:
                # This is a non-blocking version you would need to implement
                msg_middleware.refresh_connection(time_limit=0.5)
                
                # Check if we received responses
                if response_storage.get(correlation_id):
                    trips = response_storage[correlation_id]
                    break
                    
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            
    return render_template("index.html", trips=trips)


def main():
    logger.info("Starting Flask app...")
    app.run()
