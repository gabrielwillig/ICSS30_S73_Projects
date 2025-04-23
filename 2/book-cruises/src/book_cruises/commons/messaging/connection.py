from pika import BlockingConnection, ConnectionParameters, PlainCredentials


def create_connection(host: str, username: str, password: str) -> BlockingConnection:
    """Creates and returns a RabbitMQ connection."""
    credentials = PlainCredentials(username, password)
    parameters = ConnectionParameters(host, credentials=credentials)
    return BlockingConnection(parameters)
