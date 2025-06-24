import psycopg2
from psycopg2.extras import RealDictCursor
from book_cruises.commons.utils import logger


class Database:
    def __init__(
        self,
        host="localhost",
        database="book-cruises",
        user="user",
        password="password",
        port=5432,
    ):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.connection = None

    def initialize(self):
        try:
            # Establish connection to PostgreSQL
            self.connection = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
            )
            logger.info(f"PostgreSQL initialized with database: {self.database}")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL: {e}")
            raise e

    def execute_query(self, query: str, params=None):
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)

                if cursor.description:
                    result = cursor.fetchall()
                    logger.debug(f"Query returned data: {cursor.rowcount} row(s).")
                    return result
                else:
                    logger.debug(f"Query executed: {cursor.rowcount} row(s) affected (no data returned).")
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            self.connection.rollback()
            raise

    def commit(self):
        """Commits the current transaction."""
        try:
            self.connection.commit()
            logger.debug("Transaction committed.")
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            raise
    
    def rollback(self):
        """Rolls back the current transaction."""
        try:
            self.connection.rollback()
            logger.debug("Transaction rolled back.")
        except Exception as e:
            logger.error(f"Failed to roll back transaction: {e}")
            raise

    def execute_many(self, query: str, data: list):
        try:
            with self.connection.cursor() as cursor:
                psycopg2.extras.execute_values(cursor, query, data)
                self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to execute many queries: {e}")
            self.connection.rollback()
            raise e
        logger.info("Data inserted successfully.")

    def close_connection(self):
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed.")
