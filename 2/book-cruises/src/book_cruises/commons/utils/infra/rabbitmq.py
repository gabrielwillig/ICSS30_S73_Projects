import pika
from book_cruises.commons.utils import logger


class RabbitMQ:
    def __init__(self, host: str, username: str, password: str, queues: list[str]):
        self.__host = host
        self.__queues = queues
        self.__username = username
        self.__password = password
        self.__connection = None
        self.__channel = None
    
    def is_connected(self) -> bool:
        """Check if the RabbitMQ connection is established."""
        return self.__connection and self.__connection.is_open

    def initialize(self):
        try:
            credentials = pika.PlainCredentials(username=self.__username, password=self.__password)
            parameters = pika.ConnectionParameters(host=self.__host, credentials=credentials)

            # Establish connection to RabbitMQ
            self.__connection = pika.BlockingConnection(parameters)
            self.__channel = self.__connection.channel()

            # Declare all queues
            for queue in self.__queues:
                self.__channel.queue_declare(queue=queue)
                logger.info(f"RabbitMQ initialized with queue: {queue}")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ: {e}")
            raise e

    def declare_exclusive_queue(self, queue_name: str) -> str:
        try:
            result = self.__channel.queue_declare(
                queue=queue_name,
                exclusive=True,  # Automatically delete the queue when the client disconnects
            )
            logger.info(f"Created temporary queue: {result.method.queue}")
            return result.method.queue
        except Exception as e:
            logger.error(f"Failed to create temporary queue {queue_name}: {e}")
            raise e

    def publish_message(self, queue_name:str, message: str, properties: dict = None):
        try:
            if not self.__channel:
                logger.error("RabbitMQ channel is not initialized.")
                return
            
            # Add correlation_id to message properties
            basic_properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                correlation_id=properties.get("correlation_id", None),
                reply_to=properties.get("reply_to", None),
            )

            # Publish a message to the queue
            self.__channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=message,
                properties=basic_properties,
            )
            logger.info(f"Message published to queue {queue_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise e

    def consume_messages(self, queue_callbacks: dict[str, callable]):
        try:
            if not self.__channel:
                logger.error("RabbitMQ channel is not initialized.")
                return

            # Start consuming messages for each queue with its respective callback
            for queue, callback in queue_callbacks.items():
                self.__channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)
                logger.info("Set callback for queue: %s", queue)
            # self.__channel.start_consuming()
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
            raise e
    
    def start_consuming(self):
        try:
            if not self.__channel:
                logger.error("RabbitMQ channel is not initialized.")
                return

            # Start consuming messages
            self.__channel.start_consuming()
        except Exception as e:
            logger.error(f"Failed to start consuming messages: {e}")
            raise e

    def refresh_connection(self, time_limit: float = 0.5):
        if self.__connection:
            try:
                self.__connection.process_data_events(time_limit=time_limit)
            except pika.exceptions.AMQPConnectionError as e:
                logger.error(f"Connection error: {e}")
                self.close_connection()
                self.initialize()
        else:
            logger.error("No active RabbitMQ connection to refresh.")

    def close_connection(self):
        if self.__connection:
            self.__connection.close()
            logger.info("RabbitMQ connection closed.")
