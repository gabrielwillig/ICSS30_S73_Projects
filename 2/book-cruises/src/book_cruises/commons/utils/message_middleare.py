import time
from typing import Callable 
from concurrent.futures import ThreadPoolExecutor
from book_cruises.commons.utils import logger
from .infra import RabbitMQ

class MessageMiddleware:
    def __init__(self, host: str, queue_name: str, username: str, password: str):
        self.rabbitmq = RabbitMQ(host=host, queue_name=queue_name, username=username, password=password)

        self.max_retries = 10  # or set as you prefer
        self.initial_backoff = 1  # seconds
        self.max_backoff = 60  # seconds
        self.backoff_multiplier = 2
    
    def initialize(self):
        # Initialize the RabbitMQ connection
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.rabbitmq.initialize()
                break
            except Exception as e:
                retry_count += 1
                backoff = min(
                    self.initial_backoff * (self.backoff_multiplier ** (retry_count - 1)),
                    self.max_backoff
                )
                logger.error(f"Failed to initialize RabbitMQ (attempt {retry_count}/{self.max_retries}): {str(e)}")
                logger.warning(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            finally:
                if retry_count == self.max_retries:
                    logger.error("Max retries reached. Exiting.")
                    raise e

    def publish_message(self, message: str):
        self.rabbitmq.publish_message(message)
    
    def consume_messages(self, callback: Callable):
        self.callback = callback

        retry_count = 0
        while True:
            try:
                # Try to consume messages
                self.rabbitmq.consume_messages(self.__process_message)
                # If consume_messages returns (it shouldn't unless stopped), reset retries
                retry_count = 0
            except ConnectionError as e:
                retry_count += 1
                if retry_count > self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded. Giving up.")
                    raise
                
                # Calculate backoff time with exponential backoff
                backoff = min(
                    self.initial_backoff * (self.backoff_multiplier ** (retry_count - 1)),
                    self.max_backoff
                )
                
                logger.warning(
                    f"Broker connection failed (attempt {retry_count}/{self.max_retries}). "
                    f"Retrying in {backoff} seconds. Error: {str(e)}"
                )
                time.sleep(backoff)
            except Exception as e:
                # Handle other unexpected errors
                logger.error(f"Unexpected error in message consumption: {str(e)}")
                raise
    
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