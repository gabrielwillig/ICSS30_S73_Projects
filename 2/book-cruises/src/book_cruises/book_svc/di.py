import inject
from book_cruises.commons.utils import MessageMiddleware, Database, config
from book_cruises.commons.utils import logger

def configure_dependencies(binder: inject.Binder) -> None:
    queues = [config.BOOK_SVC_QUEUE, config.BOOK_SVC_RESPONSE_QUEUE]

    msg_middleware = MessageMiddleware(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
        queues=queues
    )

    database = Database(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )

    binder.bind(Database, database)
    binder.bind(MessageMiddleware, msg_middleware)

def initialize_dependencies():

    inject.configure(configure_dependencies)
    inject.instance(Database).initialize()  
    inject.instance(MessageMiddleware).initialize()
    logger.info("Dependencies initialized")