"""Persistence utilities for storing and retrieving data."""

import pickle
import os
from datetime import datetime
from typing import Set, Dict, Any, Union
from src.utils.logger import app_logger

def _convert_to_timestamp(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert datetime objects to ISO format strings in a dictionary.
    
    Args:
        data (dict): Dictionary possibly containing datetime objects
        
    Returns:
        dict: Dictionary with datetime objects converted to ISO format strings
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

def save_data(data: Any, filename: str) -> None:
    """Save data to a pickle file.
    
    Args:
        data: Data to save
        filename (str): Name of the file to save to
    """
    try:
        # Convert any datetime objects to timestamps before saving
        if isinstance(data, dict):
            data = {k: _convert_to_timestamp(v) if isinstance(v, dict) else v for k, v in data.items()}
        
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
    except Exception as e:
        app_logger.error(f"Failed to save data to {filename}: {str(e)}")

def load_data(filename: str, default: Any = None) -> Any:
    """Load data from a pickle file.
    
    Args:
        filename (str): Name of the file to load from
        default: Default value to return if file doesn't exist or load fails
        
    Returns:
        Data loaded from the file or default value
    """
    if not os.path.exists(filename):
        return default
    
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            return data
    except Exception as e:
        app_logger.error(f"Failed to load data from {filename}: {str(e)}")
        return default
