import time
from .infra import Postgres
from book_cruises.commons.utils import logger

class Database:
    def __init__(self, host: str, database: str, user: str, password: str, port: int):
        self.postgres = Postgres(host=host, database=database, user=user, password=password, port=port)

        self.max_retries = 5  # or set as you prefer
        self.initial_backoff = 1
        self.max_backoff = 60
        self.backoff_multiplier = 2

    def initialize(self):
        # Initialize the PostgreSQL connection
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.postgres.initialize()
                break
            except Exception as e:
                retry_count += 1
                backoff = min(
                    self.initial_backoff * (self.backoff_multiplier ** (retry_count - 1)),
                    self.max_backoff
                )
                logger.error(f"Failed to initialize PostgreSQL (attempt {retry_count}/{self.max_retries}): {str(e)}")
                logger.warning(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            finally:
                if retry_count == self.max_retries:
                    logger.error("Max retries reached. Exiting.")
                    raise e

    def execute_query(self, query: str, params=None):
        return self.postgres.execute_query(query, params)

    def close_connection(self):
        self.postgres.close_connection()