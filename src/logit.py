import os
import logging

# Get DEBUG flag from environment variable
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

def log(message):
    """
    Log a message if DEBUG is enabled.
    The ONLY print function that should be used in any container.
    """
    if DEBUG:
        print(message, flush=True)

def get_logger(name):
    """
    Get a properly configured logger instance for a module.
    This is the preferred way for modules to get their own logger.
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    # Set level based on DEBUG flag
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    return logger 