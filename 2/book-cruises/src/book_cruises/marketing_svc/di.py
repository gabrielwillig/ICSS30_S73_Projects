import inject
from book_cruises.commons.messaging import Producer
from book_cruises.commons.database import Database
from book_cruises.commons.utils import logger, config

def __configure_dependencies(binder: inject.Binder) -> None:
    # Create database connection
    database = Database(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )

    # Create producer for sending promotions
    producer = Producer(
        host=config.RABBITMQ_HOST,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
    )

    # Bind instances to their types
    binder.bind(Database, database)
    binder.bind(Producer, producer)

def configure_dependencies():
    inject.configure(__configure_dependencies)
    logger.info("Marketing Service dependencies configured")