from typing import Callable 
from concurrent.futures import ThreadPoolExecutor
from book_cruises.commons.utils import logger
from .infra import RabbitMQ

class MessageMiddleware:
    def __init__(self, host: str, queue_name: str, username: str, password: str):
        self.rabbitmq = RabbitMQ(host=host, queue_name=queue_name, username=username, password=password)
        self.rabbitmq.initialize()
    
    def publish_message(self, message: str):
        self.rabbitmq.publish_message(message)
    
    def consume_messages(self, callback: Callable):
        self.callback = callback
        self.rabbitmq.consume_messages(self.__process_message)
    
    def __process_message(self, channel, method, properties, body):
        try:
            # Deserialize the message (assuming JSON format)
            message = body.decode("utf-8")
            logger.info(f"Received message: {message}")

            # Call the callback function to process the message
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self.callback, message)
                result = future.result()

            # Acknowledge the message
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    def close_connection(self):
        self.rabbitmq.close_connection()