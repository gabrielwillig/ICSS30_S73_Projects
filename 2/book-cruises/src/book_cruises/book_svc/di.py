import inject
from book_cruises.commons.utils import Consumer, Database, config
from book_cruises.commons.utils import logger

def configure_dependencies(binder: inject.Binder) -> None:

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

def initialize_dependencies():

    inject.configure(configure_dependencies)
    inject.instance(Database).initialize()  
    inject.instance(Consumer)
    logger.info("Dependencies initialized")