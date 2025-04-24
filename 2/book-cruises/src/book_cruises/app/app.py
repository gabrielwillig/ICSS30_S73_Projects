import json
import random
import time
import threading
import uuid
from flask import Flask, render_template, request, session, jsonify, Response, stream_with_context
from book_cruises.commons.utils import config, logger
from book_cruises.commons.messaging import Producer, Consumer
from .di import configure_dependencies, get_producer, get_consumer

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "mySecretAppKey"  # Add a secret key for sessions
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
        queue_name = f"{destination.lower()}_consumer_{uuid.uuid4().hex}"

        exchange_name = f"{destination.lower()}_promotions_exchange"

        consumer.exchange_declare(exchange_name, exchange_type="fanout")

        consumer.declare_queue(queue_name)

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
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Helps with certain proxies
        }
    )

def main():
    logger.info("Starting Flask app...")
    app.run()
