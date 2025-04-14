from book_cruises.commons.utils.infra.postgres import Postgres
from book_cruises.commons.utils import config, logger

def initialize_itineraries_table(postgres: Postgres):
    
    # Create the itineraries table if it doesn't exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS itineraries (
        id SERIAL PRIMARY KEY,
        destination VARCHAR(255) NOT NULL,
        date DATE NOT NULL,
        harbor VARCHAR(255) NOT NULL
    );
    """
    postgres.execute_query(create_table_query)

    # Check if the table is empty
    check_table_query = "SELECT COUNT(*) AS count FROM itineraries;"
    result = postgres.execute_query(check_table_query)
    if result and result[0]["count"] == 0:
        # Insert dummy data only if the table is empty
        insert_data_query = """
        INSERT INTO itineraries (destination, date, harbor)
        VALUES
            ('Bahamas', '2025-04-20', 'Nassau'),
            ('Caribbean', '2025-05-15', 'San Juan');
        """
        postgres.execute_query(insert_data_query)
        logger.info("Dummy data inserted into the itineraries table.")
    else:
        logger.info("Itineraries table already contains data. Skipping data insertion.")


def initialize_database():
    postgres = Postgres(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT
    )
    postgres.initialize()

    # Initialize each table
    initialize_itineraries_table(postgres)
    postgres.close_connection()

if __name__ == "__main__":
    initialize_database()