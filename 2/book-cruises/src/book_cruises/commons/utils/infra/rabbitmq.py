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

    def publish_message(self, queue_name:str, message: str, properties: dict = None):
        try:
            if not self.__channel:
                logger.error("RabbitMQ channel is not initialized.")
                return
            
            # Add correlation_id to message properties
            basic_properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                correlation_id=properties.get("correlation_id") if properties else None
            )

            # Publish a message to the queue
            self.__channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=message,
                properties=basic_properties
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
                if queue not in self.__queues:
                    raise ValueError(f"Queue {queue} is not declared.")
                self.__channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)
                logger.info("Set callback for queue: %s", queue)
            self.__channel.start_consuming()
        except Exception as e:
            logger.error(f"Failed to consume messages: {e}")
            raise e

    def close_connection(self):
        if self.__connection:
            self.__connection.close()
            logger.info("RabbitMQ connection closed.")
