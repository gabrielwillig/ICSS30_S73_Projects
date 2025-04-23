import inject
from book_cruises.commons.messaging import Producer
from book_cruises.commons.utils import config

def configure_dependencies(binder: inject.Binder) -> None:
    queues = [config.BOOK_SVC_QUEUE]

    producer = Producer(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
    )

    binder.bind(Producer, producer)

def config_dependencies():
    inject.configure(configure_dependencies)
    inject.instance(Producer)

def get_rabbitmq_producer() -> Producer:
    return inject.instance(Producer)