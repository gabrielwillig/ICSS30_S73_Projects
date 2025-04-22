import inject
from book_cruises.commons.utils import config, RabbitMQProducer

def configure_dependencies(binder: inject.Binder) -> None:
    queues = [config.BOOK_SVC_QUEUE]

    producer = RabbitMQProducer(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
    )

    binder.bind(RabbitMQProducer, producer)

def config_dependencies():
    inject.configure(configure_dependencies)
    inject.instance(RabbitMQProducer)

def get_rabbitmq_producer() -> RabbitMQProducer:
    return inject.instance(RabbitMQProducer)