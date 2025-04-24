import json
import random
import time
import threading
import pika
from flask import Flask, render_template, request, session, jsonify, Response, stream_with_context
from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Producer, Consumer
from .di import configure_dependencies, get_producer, get_consumer
# Add this to your imports at the top
from book_cruises.commons.messaging.connection import create_connection

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "pindamonhangaba"  # Add a secret key for sessions
flask_configs = {
    "debug": config.DEBUG,
    "host": config.HOST,
    "port": config.PORT,
    "user_reloader": config.DEBUG,
}
app.config.from_mapping(flask_configs)

configure_dependencies()
producer: Producer = get_producer()
consumer: Consumer = get_consumer()

# Simple in-memory payment tracking
payment_statuses = {}

def process_payment_after_delay(payment_id):
    """Background task to process payment after a delay"""
    logger.info(f"Started payment processing for {payment_id}")
    
    # Sleep for 5-10 seconds to simulate payment processing
    time.sleep(random.uniform(5, 10))
    
    # Randomly approve or decline the payment
    if random.random() < 0.8:  # 80% chance of success
        payment_statuses[payment_id] = "success"
        logger.info(f"Payment {payment_id} approved")
    else:
        payment_statuses[payment_id] = "error"
        logger.info(f"Payment {payment_id} declined")

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
        
        return render_template("book.html", trip_id=trip_id, price=price, departure_date=departure_date)
    except Exception as e:
        logger.error(f"Failed to process payment: {e}")
        return "An error occurred while processing your request.", 500

@app.route("/payment", methods=["POST"])
def payment():
    try:
        trip_id = request.form.get("trip_id")
        price = request.form.get("price")
        passengers = request.form.get("passengers", 1)
        
        # Store payment information in the session
        session["payment_info"] = {
            "trip_id": trip_id,
            "price": price,
            "passengers": passengers,
            "timestamp": time.time()
        }
        
        # Generate a unique payment ID
        payment_id = f"{trip_id}-{int(time.time())}"
        
        # Set initial payment status to "processing"
        payment_statuses[payment_id] = "processing"
        
        # Store payment_id in session for status check
        session["payment_id"] = payment_id
        
        # Start with processing state
        logger.info(f"Started payment process ID {payment_id} with price ${price} for {passengers} passengers")
        
        # Start background thread to process payment after delay
        payment_thread = threading.Thread(
            target=process_payment_after_delay,
            args=(payment_id,)  # Fix: Add comma to make this a tuple
        )
        payment_thread.daemon = True
        payment_thread.start()
        
        # Return the payment processing page with initial "processing" status
        return render_template(
            "payment.html", 
            price=price,
            payment_id=payment_id,
            passengers=passengers,
            payment_status="processing"
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

@app.route('/subscribe/<destination>')
def subscribe_to_promotions(destination):
    """Subscribe to promotions for a specific destination using Server-Sent Events"""
    def generate():
        # Normalize destination name
        queue_name = f"{destination.lower()}_promotions"
        
        logger.info(f"Client subscribed to promotions for {destination}")
        
        # Create a new connection for this client
        connection = create_connection(
            config.RABBITMQ_HOST,
            config.RABBITMQ_USERNAME, 
            config.RABBITMQ_PASSWORD
        )
        channel = connection.channel()
        
        # Ensure queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        
        # Keep track of messages we've already sent to this client
        processed_messages = set()
        
        try:
            # First, process any messages already in the queue
            while True:
                method_frame, header_frame, body = channel.basic_get(
                    queue=queue_name, 
                    auto_ack=False
                )
                
                if not method_frame:
                    # No more messages in queue
                    break
                    
                if body:
                    # Create a message identifier based on content
                    message_id = hash(body)
                    
                    # Only send if we haven't sent it before
                    if message_id not in processed_messages:
                        logger.info(f"Sending existing promotion to client: {body}")
                        yield f"data: {body.decode()}\n\n"
                        processed_messages.add(message_id)
                    
                    # Reject with requeue=True to keep in queue for other consumers
                    channel.basic_reject(
                        delivery_tag=method_frame.delivery_tag, 
                        requeue=True
                    )
            
            # Then poll for new messages
            while True:
                method_frame, header_frame, body = channel.basic_get(
                    queue=queue_name, 
                    auto_ack=False
                )
                
                if method_frame and body:
                    # Create a message identifier
                    message_id = hash(body)
                    
                    # Only send if we haven't sent it before
                    if message_id not in processed_messages:
                        logger.info(f"Sending new promotion to client: {body}")
                        yield f"data: {body.decode()}\n\n"
                        processed_messages.add(message_id)
                    
                    # Reject with requeue=True to keep in queue for other consumers
                    channel.basic_reject(
                        delivery_tag=method_frame.delivery_tag, 
                        requeue=True
                    )
                
                # Wait before checking again to avoid hammering the queue
                time.sleep(1)
                
        except GeneratorExit:
            logger.info(f"Client unsubscribed from {destination} promotions")
        finally:
            # Clean up connection
            if connection and connection.is_open:
                connection.close()
                logger.info(f"Closed connection for {destination} promotion subscriber")

    # Use Flask's streaming response with correct SSE headers
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )

def main():
    logger.info("Starting Flask app...")
    app.run()
