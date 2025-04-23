from pydantic_settings import BaseSettings

class Config(BaseSettings):
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "localhost"  
    RABBITMQ_USERNAME: str = "user"  
    RABBITMQ_PASSWORD: str = "password"  

    # RabbitMQ Queues
    BOOK_SVC_QUEUE: str = "book_svc_queue"  
    RESERVE_CREATED_QUEUE: str = "reserve_created_queue"

    # PostgreSQL Configuration
    DB_HOST: str = "localhost"
    DB_NAME: str = "book-cruises"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_PORT: int = 5432

    # App Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEBUG: bool = True

    # Logging Configuration
    LOG_LEVEL: str = "DEBUG" if DEBUG else "INFO"  # Set to DEBUG if DEBUG is True, otherwise INFO

    class Config:
        env_file = ".env"  # Load environment variables from a .env file if present
        env_file_encoding = "utf-8"

# Create a single instance of the configuration
config = Config()