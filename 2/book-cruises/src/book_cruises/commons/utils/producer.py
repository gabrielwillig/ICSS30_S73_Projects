import threading
import uuid
import json
from time import sleep
from pika import ConnectionParameters, BlockingConnection, PlainCredentials, BasicProperties
from pika.exceptions import StreamLostError, AMQPConnectionError
from book_cruises.commons.utils import logger

@DeprecationWarning
class Producer(threading.Thread):
    def __init__(self, host, username, password, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.daemon = True
        self.is_running = True
        self.name = "ThreadedProducer"
        self.response_storage = {}  # Temporary storage for responses
        self.lock = threading.Lock()  # Thread-safe access to response storage

        # RabbitMQ connection setup
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None

        self._connect()

    def _connect(self):
        """Establish a connection to RabbitMQ."""
        try:
            credentials = PlainCredentials(self.username, self.password)
            parameters = ConnectionParameters(self.host, credentials=credentials)
            self.connection = BlockingConnection(parameters)
            self.channel = self.connection.channel()

            logger.info("Connected to RabbitMQ")
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def is_connected(self):
        """Check if the RabbitMQ connection is established."""
        return self.connection and self.connection.is_open

    def run(self):
        """Keep the connection alive and process data events."""
        while self.is_running:
            try:
                self.connection.process_data_events(time_limit=1)
            except StreamLostError as e:
                logger.error(f"Stream connection lost: {e}. Reconnecting...")
                self._connect()

    def _publish(self, queue, message, properties):
        """Internal method to publish a message."""
        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=message.encode(),
                properties=properties,
            )
        except StreamLostError as e:
            logger.error(f"Stream connection lost during publish: {e}. Reconnecting...")
            self._connect()
            self._publish(queue, message, properties)

    def publish(self, queue, message, correlation_id, reply_to):
        """Publish a message with correlation_id and reply_to."""
        properties = BasicProperties(
            correlation_id=correlation_id,
            reply_to=reply_to,
        )
        self.connection.add_callback_threadsafe(
            lambda: self._publish(queue, json.dumps(message), properties)
        )

    def create_temporary_queue(self):
        """Create a temporary queue for receiving responses."""
        try:
            result = self.channel.queue_declare(queue="", exclusive=True, auto_delete=True)
            return result.method.queue
        except StreamLostError as e:
            logger.error(f"Stream connection lost during queue creation: {e}. Reconnecting...")
            self._connect()
            return self.create_temporary_queue()

    def consume_response(self, queue_name, correlation_id, timeout=5):
        """Consume a response from the specified queue."""
        def callback(ch, method, properties, body):
            with self.lock:
                if properties.correlation_id == correlation_id:
                    self.response_storage[correlation_id] = json.loads(body)
                    logger.info(f"Received response for correlation_id {correlation_id}: {body}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)

        try:
            self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
            self.connection.process_data_events(time_limit=timeout)
        except StreamLostError as e:
            logger.error(f"Stream connection lost during consume: {e}. Reconnecting...")
            self._connect()
            return self.consume_response(queue_name, correlation_id, timeout)

        with self.lock:
            return self.response_storage.pop(correlation_id, None)

    def stop(self):
        """Stop the producer and close the connection."""
        logger.info("Stopping ThreadedProducer...")
        self.is_running = False
        try:
            self.connection.process_data_events(time_limit=1)
            if self.connection.is_open:
                self.connection.close()
        except Exception as e:
            logger.error(f"Error while stopping ThreadedProducer: {e}")
        logger.info("ThreadedProducer stopped.")


if __name__ == "__main__":
    producer = Producer(
        host="localhost",
        username="guest",
        password="guest",
    )
    producer.start()

    try:
        for i in range(5):
            correlation_id = str(uuid.uuid4())
            reply_to_queue = producer.create_temporary_queue()

            # Publish a message
            message = {
                "departure_date": "2026-01-01",
                "departure_harbor": "San Juan",
                "arrival_harbor": "Miami",
            }
            producer.publish("rpc_queue", message, correlation_id, reply_to_queue)

            # Consume the response
            response = producer.consume_response(reply_to_queue, correlation_id, timeout=5)
            if response:
                print(f"Received response: {response}")
            else:
                print("No response received within the timeout period.")

    except KeyboardInterrupt:
        producer.stop()
    finally:
        producer.join()
