from pydantic_settings import BaseSettings

class Config(BaseSettings):
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_USERNAME: str = "user"
    RABBITMQ_PASSWORD: str = "password"

    # RabbitMQ Exchanges
    APP_EXCHANGE: str = "app_exchange"
    PROMOTIONS_EXCHANGE: str = "promotions_exchange"  # Exchange for promotions

    # RabbitMQ Queues
    QUERY_RESERVATION_QUEUE: str = "query_reservation_queue"
    RESERVE_CREATED_QUEUE: str = "reserve_created_queue"
    APPROVED_PAYMENT_TICKET_QUEUE: str = "approved_payment_ticket_queue"
    APPROVED_PAYMENT_BOOK_SVC_QUEUE: str = "approved_payment_book_svc_queue"
    REFUSED_PAYMENT_QUEUE: str = "refused_payment_queue"
    TICKET_GENERATED_QUEUE: str = "ticket_generated_queue"

    # RabbitMQ Routing Keys
    APPROVED_PAYMENT_ROUTING_KEY: str = "approved_payment"

    # WEB Server Debug Configuration
    DEBUG: bool = True

    # App Configuration
    APP_PORT: int = 5000
    APP_HOST: str = "localhost"

    # Book Service Configuration
    BOOK_SVC_WEB_SERVER_PORT: int = 5001
    BOOK_SVC_WEB_SERVER_HOST: str = "localhost"  # Host for the Book Service web server

    # Payment Service Configuration
    PAYMENT_SVC_WEB_SERVER_PORT: int = 5002
    PAYMENT_SVC_WEB_SERVER_HOST: str = "localhost"  # Host for the Payment Service web server

    # PostgreSQL Configuration
    DB_HOST: str = "localhost"
    DB_NAME: str = "book-cruises"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_PORT: int = 5432

    REQUEST_TIMEOUT: int = 5  # Timeout for HTTP requests in seconds

    # Logging Configuration
    LOG_LEVEL: str = "DEBUG" if DEBUG else "INFO"  # Set to DEBUG if DEBUG is True, otherwise INFO

    book_svc_queue: str = "book_svc_queue"

    class Config:
        env_file = ".env"  # Load environment variables from a .env file if present
        env_file_encoding = "utf-8"

# Create a single instance of the configuration
config = Config()