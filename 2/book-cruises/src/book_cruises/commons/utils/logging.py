import logging
import traceback
from .config import config

# ANSI escape codes for colors
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"

# Create a logger
logger = logging.getLogger("book_cruises")
logger.setLevel(config.LOG_LEVEL)  # Set the log level from the config

# Custom formatter to add colors
class ColorFormatter(logging.Formatter):
    def format(self, record):
        # Format the base message
        formatted_message = super().format(record)

        # Check for log level and apply colors
        if record.levelno == logging.DEBUG:
            return f"{BLUE}{formatted_message}{RESET}"
        elif record.levelno == logging.INFO:
            return f"{GREEN}{formatted_message}{RESET}"
        elif record.levelno == logging.WARNING:
            return f"{YELLOW}{formatted_message}{RESET}"
        elif record.levelno == logging.ERROR:
            # If there's an exception, include the traceback in red
            if record.exc_info:
                exception_message = "".join(traceback.format_exception(*record.exc_info))
                return f"{RED}{formatted_message}\n{exception_message}{RESET}"
            return f"{RED}{formatted_message}{RESET}"
        return formatted_message

# Create a formatter
formatter = ColorFormatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)

# Prevent duplicate logs in case of multiple imports
logger.propagate = False

if __name__ == "__main__":
    logger.info("Logging system initialized.")