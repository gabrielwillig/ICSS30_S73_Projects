import inject
from book_cruises.commons.utils import MessageMidleware, Database, config

def configure_dependencies(binder: inject.Binder) -> None:
    msg_middleware = MessageMidleware(
        host=config.RABBITMQ_HOST,
        queue_name=config.BOOK_SVC_QUEUE,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD
    )

    binder.bind(MessageMidleware, msg_middleware)