import inject
from book_cruises.commons.utils import MessageMiddleware, config

def configure_dependencies(binder: inject.Binder) -> None:
    queues = [config.BOOK_SVC_QUEUE]

    msg_middleware = MessageMiddleware(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
        queues=queues
    )

    binder.bind(MessageMiddleware, msg_middleware)

def initialize_dependencies():
    inject.configure(configure_dependencies)
    inject.instance(MessageMiddleware).initialize()

def get_message_middleware() -> MessageMiddleware:
    return inject.instance(MessageMiddleware)