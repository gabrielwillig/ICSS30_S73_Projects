from .infra import Postgres
from book_cruises.commons.utils import logger

class Database:
    def __init__(self, host: str, database: str, user: str, password: str, port: int):
        self.postgres = Postgres(host=host, database=database, user=user, password=password, port=port)
    
    def initialize(self):
        # Initialize the PostgreSQL connection
        self.postgres.initialize()

    def execute_query(self, query: str, params=None):
        return self.postgres.execute_query(query, params)

    def close_connection(self):
        self.postgres.close_connection()