from datetime import datetime, timedelta
import random

from book_cruises.commons.utils import config, logger
from .database import Database


def generate_dummy_data():
    # Generate dummy data for the itineraries table
    ships = ["Oceanic Voyager", "Caribbean Explorer", "Bahamas Dream", "Atlantic Star"]
    harbors = ["Miami", "Nassau", "San Juan", "Kingston", "Havana"]
    dummy_data = []

    for _ in range(100):
        ship = random.choice(ships)
        departure_date = datetime.now().date() + timedelta(days=random.randint(1, 365))
        departure_time = (
            datetime.min + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
        ).time()
        departure_harbor = random.choice(harbors)
        arrival_harbor = random.choice([h for h in harbors if h != departure_harbor])
        arrival_date = departure_date + timedelta(days=random.randint(1, 10))
        visiting_harbors = random.sample(harbors, random.randint(1, len(harbors) - 1))
        number_of_days = (arrival_date - departure_date).days
        price = round(random.uniform(500, 5000), 2)

        dummy_data.append(
            (
                ship,
                departure_date,
                departure_time,
                departure_harbor,
                arrival_harbor,
                arrival_date,
                visiting_harbors,
                number_of_days,
                price,
            )
        )

    return dummy_data


def initialize_itineraries_table(database: Database):
    # Create the itineraries table if it doesn't exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS itineraries (
        id SERIAL PRIMARY KEY,
        ship VARCHAR(255) NOT NULL,
        departure_date DATE NOT NULL,
        departure_time TIME NOT NULL,
        departure_harbor VARCHAR(255) NOT NULL,
        arrival_harbor VARCHAR(255) NOT NULL,
        arrival_date DATE NOT NULL,
        visiting_harbors TEXT[],
        number_of_days INT NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT transaction_timestamp(),
        updated_at TIMESTAMP DEFAULT transaction_timestamp()
    );
    """
    database.execute_query(create_table_query)

    # Check if the table is empty
    check_table_query = "SELECT COUNT(*) AS count FROM itineraries;"
    result = database.execute_query(check_table_query)
    if result and result[0]["count"] == 0:
        dummy_data = generate_dummy_data()
        logger.info("Inserting dummy data into the itineraries table...")

        # Insert dummy data into the database
        insert_data_query = """
        INSERT INTO itineraries (
            ship, departure_date, departure_time, departure_harbor, 
            arrival_harbor, arrival_date, 
            visiting_harbors, number_of_days, price
        ) VALUES %s;
        """
        database.execute_many(insert_data_query, dummy_data)
        logger.info("Dummy data inserted into the itineraries table.")
    else:
        logger.info("Itineraries table already contains data. Skipping data insertion.")


def initialize_database():
    database = Database(
        host=config.DB_HOST,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        port=config.DB_PORT,
    )
    database.initialize()

    # Initialize each table
    initialize_itineraries_table(database)
    database.close_connection()


if __name__ == "__main__":
    initialize_database()
