import logging
from logging import Logger

def create_logger(is_production, log_url):
    if is_production == "yes":
        logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(), logging.FileHandler(log_url)]
        )

    else:
        logging.basicConfig(
            level=logging.INFO,  # Set the logging level
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
            datefmt='%Y-%m-%d %H:%M:%S'  # Date format
        )
    logger:Logger = logging.getLogger(__name__)
    return logger
