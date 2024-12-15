"""Logging utilities for the goal bot."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(name, log_file, level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
    """Set up a logger with file and console handlers.
    
    Args:
        name (str): Name of the logger
        log_file (str): Path to the log file
        level (int): Logging level
        max_bytes (int): Maximum size of log file before rotation
        backup_count (int): Number of backup files to keep
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Create file handler
    file_handler = RotatingFileHandler(
        f'logs/{log_file}',
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)
    
    # Create console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Create main application logger
app_logger = setup_logger('goal_bot', 'goal_bot.log')

# Create webhook logger for Discord interactions
webhook_logger = setup_logger('webhook', 'webhook.log')
