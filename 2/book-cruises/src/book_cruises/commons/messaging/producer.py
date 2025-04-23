# messaging/producer.py

import uuid
import json
import threading
import time
from pika import BasicProperties

from .connection import create_connection


class RabbitMQProducer:
    def __init__(self, host, username, password):
        self.connection = create_connection(host, username, password)
        self.channel = self.connection.channel()
        self.response = None
        self.lock = threading.Lock()
        self.responses = {}

    def _ensure_channel(self):
        """Ensure the channel is open before publishing."""
        if not self.connection or self.connection.is_closed:
            self.connection = create_connection(self.host, self.username, self.password)

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()

    def _on_response(self, ch, method, props, body):
        correlation_id = props.correlation_id
        with self.lock:
            self.responses[correlation_id] = json.loads(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def publish(self, queue, message: dict):
        self._ensure_channel()
        self.channel.queue_declare(queue=queue, durable=True)
        self.channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message).encode(),
            properties=BasicProperties(content_type="application/json", delivery_mode=2),
        )

    def rpc_publish(self, queue, message: dict, timeout=5):
        self._ensure_channel()
        correlation_id = str(uuid.uuid4())
        result = self.channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=callback_queue, on_message_callback=self._on_response, auto_ack=False
        )

        self.channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message).encode(),
            properties=BasicProperties(
                reply_to=callback_queue,
                correlation_id=correlation_id,
                content_type="application/json",
                delivery_mode=2,
            ),
        )

        start = time.time()
        while time.time() - start < timeout:
            self.connection.process_data_events(time_limit=0.2)
            with self.lock:
                if correlation_id in self.responses:
                    return self.responses.pop(correlation_id)

        return None

    def close(self):
        if self.connection.is_open:
            self.connection.close()
