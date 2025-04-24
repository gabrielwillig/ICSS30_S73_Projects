import inject
from book_cruises.commons.messaging import Producer, Consumer
from book_cruises.commons.utils import config

def __configure_dependencies(binder: inject.Binder) -> None:

    producer = Producer(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
    )

    consumer = Consumer(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
    )

    binder.bind(Producer, producer)
    binder.bind(Consumer, consumer)

def configure_dependencies():
    inject.configure(__configure_dependencies)

def get_producer() -> Producer:
    return inject.instance(Producer)

def get_consumer() -> Consumer:
    return inject.instance(Consumer)