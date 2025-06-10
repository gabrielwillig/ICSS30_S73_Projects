import uuid
import json
import threading
import time
from pika import BasicProperties
from pika.exceptions import AMQPConnectionError

from book_cruises.commons.utils import logger
from .connection import create_connection


class RabbitMQProducer:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None
        self.responses = {}

    def _ensure_channel(self):
        if not self.connection or self.connection.is_closed:
            self.connection = create_connection(self.host, self.username, self.password)
        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()

    def publish(self, routing_key: str, message: dict, exchange: str = ""):
        self._ensure_channel()
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message).encode(),
            properties=BasicProperties(content_type="application/json", delivery_mode=2),
        )
        self.close()

    def _on_response(self, ch, method, props, body):
        self.responses[props.correlation_id] = json.loads(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def rpc_publish(self, routing_key: str, message: dict, timeout=5, exchange: str = ""):
        self._ensure_channel()
        correlation_id = str(uuid.uuid4())
        result = self.channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=callback_queue,
            on_message_callback=self._on_response,
            auto_ack=False
        )

        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message).encode(),
            properties=BasicProperties(
                reply_to=callback_queue,
                correlation_id=correlation_id,
                content_type="application/json",
                delivery_mode=2,
            ),
        )

        # Start the I/O loop in a separate thread if not already running
        def consumer_loop():
            while correlation_id not in self.responses:
                try:
                    self.connection.process_data_events(time_limit=0.1)
                except AMQPConnectionError as e:
                    print(f"Lost connection while waiting for RPC reply: {e}")
                    break

        start = time.time()
        thread = threading.Thread(target=consumer_loop)
        thread.start()
        thread.join(timeout)

        self.close()

        return self.responses.pop(correlation_id, None)


    def close(self):
        if self.channel and self.channel.is_open:
            self.channel.close()
        if self.connection and self.connection.is_open:
            self.connection.close()
