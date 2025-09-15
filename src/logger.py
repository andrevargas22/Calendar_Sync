"""
Logger configuration for the calendar synchronization application.
"""
import logging
import os

def setup_logging(logger_name='calendar_sync'):
    """
    Configure and return a logger with console handler only
    
    Args:
        logger_name: Name of the logger
        
    Returns:
        configured logger instance
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    
    # If handlers already exist, return existing logger to avoid duplicate logs
    if logger.handlers:
        return logger
    
    # Set log level from environment variable or default to INFO
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logger.setLevel(getattr(logging, log_level))
    
    # Create formatter with timestamps and log levels
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create and add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Create a default logger instance that can be imported directly
logger = setup_logging()