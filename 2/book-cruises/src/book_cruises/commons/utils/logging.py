import logging

# Create a logger
logger = logging.getLogger("book_cruises")
logger.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)

# Prevent duplicate logs in case of multiple imports
logger.propagate = False

# Example usage (can be removed if not needed here)
if __name__ == "__main__":
    logger.info("Logger is configured and ready to use.")