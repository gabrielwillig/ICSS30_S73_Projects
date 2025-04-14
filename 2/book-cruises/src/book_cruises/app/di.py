import inject
from book_cruises.commons.utils import MessageMiddleware, config

def configure_dependencies(binder: inject.Binder) -> None:
    inject.clear()
    
    msg_middleware = MessageMiddleware(
        host=config.RABBITMQ_HOST,
        queue_name=config.BOOK_SVC_QUEUE,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD
    )

    binder.bind(MessageMiddleware, msg_middleware)