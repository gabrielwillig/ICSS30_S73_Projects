import pika
from book_cruises.commons.utils import logger

class RabbitMQ:
    def __init__(self, host="localhost", queue_name="default_queue", username="guest", password="guest"):
        self.host = host
        self.queue_name = queue_name
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None

    def initialize(self):
        try:
            credentials = pika.PlainCredentials(username=self.username, password=self.password)
            parameters = pika.ConnectionParameters(host=self.host, credentials=credentials)

            # Establish connection to RabbitMQ
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # Declare a queue
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            logger.info(f"RabbitMQ initialized with queue: {self.queue_name}")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ: {e}")

    def publish_message(self, message: str):
        try:
            if not self.channel:
                logger.error("RabbitMQ channel is not initialized.")
                return

            # Publish a message to the queue
            self.channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
            )
            logger.info(f"Message published to queue {self.queue_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")

    def consume_messages(self, callback):
        try:
            if not self.channel:
                logger.error("RabbitMQ channel is not initialized.")
                return

            # Start consuming messages
            self.channel.basic_consume(queue=self.queue_name, on_message_callback=callback)
            logger.info("Started consuming messages.")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")

    def close_connection(self):
        if self.connection:
            self.connection.close()
            logger.info("RabbitMQ connection closed.")