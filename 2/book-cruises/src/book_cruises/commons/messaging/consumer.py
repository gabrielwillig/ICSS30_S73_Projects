import json
from typing import Callable, Dict
from pika import BasicProperties
from book_cruises.commons.utils import logger

from .connection import create_connection


class RabbitMQConsumer:
    def __init__(self, host: str, username: str, password: str):
        self.connection = create_connection(host, username, password)
        self.channel = self.connection.channel()
        self.queue_callbacks: Dict[str, Callable[[dict], dict]] = {}

    def declare_queue(self, queue_name: str, durable: bool = True):
        """Optionally declare a queue. Can be skipped if queue exists."""
        self.channel.queue_declare(queue=queue_name, durable=durable)

    def register_callback(self, queue_name: str, callback: Callable[[dict], dict]):
        """Register a callback for an existing queue."""
        self.queue_callbacks[queue_name] = callback

        def wrapper(ch, method, properties: BasicProperties, body):
            response = callback(json.loads(body))

            if properties.reply_to and properties.correlation_id:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=properties,
                    body=json.dumps(response).encode(),
                )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue_name, on_message_callback=wrapper)

    def basic_consume(self, queue_name: str, auto_ack: bool = False) -> tuple:
        self.channel.basic_get(
            queue=queue_name,
            auto_ack=auto_ack,
        )

    def basic_reject(self, delivery_tag: int, requeue: bool = False):
        self.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)

    def start_consuming(self):
        if not self.queue_callbacks:
            raise RuntimeError("No queues registered for consumption.")
        logger.info(
            f"[*] Waiting for messages on {list(self.queue_callbacks.keys())}. To exit press CTRL+C."
        )
        self.channel.start_consuming()
        return self

    def close(self):
        if self.connection.is_open:
            self.connection.close()
