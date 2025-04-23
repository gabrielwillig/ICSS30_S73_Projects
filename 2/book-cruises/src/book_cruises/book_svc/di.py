import inject
from book_cruises.commons.messaging import Consumer
from book_cruises.commons.database import Database
from book_cruises.commons.utils import logger, config

def __configure_dependencies(binder: inject.Binder) -> None:

    consumer = Consumer(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
    )

    database = Database(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )

    binder.bind(Database, database)
    binder.bind(Consumer, consumer)

def configure_dependencies():
    inject.configure(__configure_dependencies)
    inject.instance(Database).initialize()  
    logger.info("Dependencies initialized")