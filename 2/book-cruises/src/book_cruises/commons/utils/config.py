from pydantic_settings import BaseSettings

class Config(BaseSettings):
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = "localhost"  
    BOOK_SVC_QUEUE: str = "book_svc_queue"  
    RABBITMQ_USERNAME: str = "user"  
    RABBITMQ_PASSWORD: str = "password"  

    # Other configurations can be added here

    class Config:
        env_file = ".env"  # Load environment variables from a .env file if present

# Create a single instance of the configuration
config = Config()