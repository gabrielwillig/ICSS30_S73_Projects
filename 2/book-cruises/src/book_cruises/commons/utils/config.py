from pydantic_settings import BaseSettings

class Config(BaseSettings):
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "localhost"  
    BOOK_SVC_QUEUE: str = "book_svc_queue"  
    RABBITMQ_USERNAME: str = "user"  
    RABBITMQ_PASSWORD: str = "password"  

    # PostgreSQL Configuration
    DB_HOST: str = "localhost"
    DB_NAME: str = "book-cruises"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_PORT: int = 5432

    class Config:
        env_file = ".env"  # Load environment variables from a .env file if present

# Create a single instance of the configuration
config = Config()