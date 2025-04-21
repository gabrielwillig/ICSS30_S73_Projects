import json
import uuid
import time
from typing import Callable
from concurrent.futures import ThreadPoolExecutor
from book_cruises.commons.utils import logger
from .infra import RabbitMQ


class MessageMiddleware:
    def __init__(self, host: str, username: str, password: str, queues: list[str]):
        self.__rabbitmq = RabbitMQ(host=host, username=username, password=password, queues=queues)

        self.__MAX_RETRIES = 10  # or set as you prefer
        self.__INITIAL_BACKOFF = 1  # seconds
        self.__MAX_BACKOFF = 60  # seconds
        self.__BACKOFF_MULTIPLIER = 2

        self.__response_storage = {}  # Temporary storage for responses

    def is_connected(self) -> bool:
        """Check if the RabbitMQ connection is established."""
        return self.__rabbitmq.is_connected()

    def initialize(self):
        # Initialize the RabbitMQ connection
        retry_count = 0
        while retry_count < self.__MAX_RETRIES:
            try:
                self.__rabbitmq.initialize()
                break
            except Exception as e:
                retry_count += 1
                backoff = min(
                    self.__INITIAL_BACKOFF * (self.__BACKOFF_MULTIPLIER ** (retry_count - 1)),
                    self.__MAX_BACKOFF,
                )
                logger.error(
                    f"Failed to initialize RabbitMQ (attempt {retry_count}/{self.__MAX_RETRIES}): {str(e)}"
                )
                logger.warning(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            finally:
                if retry_count == self.__MAX_RETRIES:
                    logger.error("Max retries reached. Exiting.")
                    raise e

    def publish_message(self, queue_name: str, message: str, properties: dict = None):
        self.__rabbitmq.publish_message(queue_name, message, properties)

    def create_temporary_queue(self, queue_name: str = "") -> str:
        try:
            return self.__rabbitmq.declare_exclusive_queue(queue_name)
        except Exception as e:
            logger.error(f"Failed to create temporary queue {queue_name}: {e}")
            raise e

    def consume_messages(self, queue_callbacks: dict[str, Callable]):
        wrapped_callbacks = {
            queue: self.__wrap_callback(callback) for queue, callback in queue_callbacks.items()
        }

        retry_count = 0
        while True:
            try:
                # Try to consume messages
                self.__rabbitmq.consume_messages(wrapped_callbacks)
                break  # Exit the loop if successful
                retry_count = 0
            except Exception as e:
                retry_count += 1
                if retry_count > self.__MAX_RETRIES:
                    logger.error(f"Max retries ({self.__MAX_RETRIES}) exceeded. Giving up.")
                    raise

                # Calculate backoff time with exponential backoff
                backoff = min(
                    self.__INITIAL_BACKOFF * (self.__BACKOFF_MULTIPLIER ** (retry_count - 1)),
                    self.__MAX_BACKOFF,
                )

                logger.warning(
                    f"Broker connection failed (attempt {retry_count}/{self.__MAX_RETRIES}). "
                    f"Retrying in {backoff} seconds. Error: {str(e)}"
                )
                time.sleep(backoff)

                # Reinitialize the RabbitMQ connection
                self.initialize()

    def set_response_storage(self, correlation_id: str, response: dict):
        """Store the response in the temporary storage."""
        self.__response_storage[correlation_id] = response
        logger.info(f"Stored response with ID {correlation_id}")

    def publish_consume(
        self,
        queue_name: str,
        publish_msg: str,
        callback: Callable,
        correlation_id: str = None,
    ):
        """Publish a message and consume the response."""
        correlation_id = str(uuid.uuid4())
        response_queue_id = self.create_temporary_queue()
        self.consume_messages({response_queue_id: callback})

        # Send message
        self.publish_message(
            queue_name,
            json.dumps(publish_msg),
            properties={"correlation_id": correlation_id, "reply_to": response_queue_id},
        )

        # Modified part: consume for a limited time
        timeout = time.time() + 5  # 5-second timeout

        while time.time() < timeout:
            # This is a non-blocking version you would need to implement
            self.refresh_connection(time_limit=0.5)

            # Check if we received responses
            if self.__response_storage.get(correlation_id):
                # Consume the response
                response = self.__response_storage.pop(correlation_id, None)
                if response:
                    logger.info(f"Received response: {response}")
                    return response
                else:
                    logger.warning(f"No response found for correlation ID {correlation_id}")
            time.sleep(0.1)

    def start_consuming(self):
        try:
            self.__rabbitmq.start_consuming()
        except Exception as e:
            logger.error(f"Failed to start consuming messages: {e}")
            raise e

    def refresh_connection(self, time_limit: float = 0.5):
        self.__rabbitmq.refresh_connection(time_limit=time_limit)

    def close_connection(self):
        self.__rabbitmq.close_connection()

    def __wrap_callback(self, callback: Callable) -> Callable:
        def wrapped_callback(channel, method, properties, body):
            try:
                # Deserialize the message (assuming JSON format)
                message = body.decode("utf-8")
                logger.info(f"Received message: {message}")

                # Call the original callback
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(callback, message, properties)
                    result = future.result()
            except Exception as e:
                logger.error(f"Failed to process message: {e}")

        return wrapped_callback
