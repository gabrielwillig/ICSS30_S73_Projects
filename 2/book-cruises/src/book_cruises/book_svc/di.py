import time
import inject
from functools import partial
from book_cruises.commons.utils import MessageMiddleware, Database, config
from book_cruises.commons.utils import logger

def configure_dependencies(binder: inject.Binder) -> None:
    msg_middleware = MessageMiddleware(
        host=config.RABBITMQ_HOST,
        queue_name=config.BOOK_SVC_QUEUE,
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD
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
    max_retries = 5
    initial_backoff = 1  # Start with 1 second
    backoff_multiplier = 2
    max_backoff = 32  # Maximum wait time (2^5)

    dependencies = [
        {
            'name': 'MessageMiddleware',
            'instance': partial(inject.instance, MessageMiddleware),
            'initialize': lambda x: x.initialize()
        },
        {
            'name': 'Database',
            'instance': partial(inject.instance, Database),
            'initialize': lambda x: x.initialize()
        }
    ]

    inject.configure(configure_dependencies)

    for dep in dependencies:
        retry_count = 0
        last_exception = None
        
        while retry_count < max_retries:
            try:
                instance = dep['instance']()
                dep['initialize'](instance)
                break
            except Exception as e:
                last_exception = e
                retry_count += 1
                backoff = min(initial_backoff * (backoff_multiplier ** (retry_count - 1)), max_backoff)
                
                logger.error(f"Failed to initialize {dep['name']} (attempt {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying {dep['name']} in {backoff} seconds...")
                    time.sleep(backoff)
        
        if retry_count == max_retries:
            logger.error(f"Max retries exceeded for {dep['name']}. Exiting.")
            raise RuntimeError(f"Failed to initialize {dep['name']} after {max_retries} attempts") from last_exception