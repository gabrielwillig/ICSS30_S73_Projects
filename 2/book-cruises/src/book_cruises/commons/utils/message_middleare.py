from .infra import RabbitMQ

class MessageMidleware:
    def __init__(self, host: str, queue_name: str, username: str, password: str):
        self.rabbitmq = RabbitMQ(host=host, queue_name=queue_name, username=username, password=password)
        self.rabbitmq.initialize()
    
    def publish_message(self, message: str):
        self.rabbitmq.publish_message(message)
    
    def consume_messages(self, callback):
        self.rabbitmq.consume_messages(callback)
    
    def close_connection(self):
        self.rabbitmq.close_connection()