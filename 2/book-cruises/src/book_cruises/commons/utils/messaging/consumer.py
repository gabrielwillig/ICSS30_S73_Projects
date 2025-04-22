# messaging/consumer.py

import json
from .connection import create_connection


class RabbitMQConsumer:
    def __init__(self, host, username, password, queue_name):
        self.queue_name = queue_name
        self.connection = create_connection(host, username, password)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=True)

    def start_consuming(self, on_message_callback):
        def wrapper(ch, method, properties, body):
            message = json.loads(body)
            response = on_message_callback(message)

            if properties.reply_to and properties.correlation_id:
                ch.basic_publish(
                    exchange='',
                    routing_key=properties.reply_to,
                    properties=properties,
                    body=json.dumps(response).encode()
                )

            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=wrapper)
        print(f"[*] Waiting for messages on queue '{self.queue_name}'. To exit press CTRL+C.")
        self.channel.start_consuming()

    def close(self):
        if self.connection.is_open:
            self.connection.close()
