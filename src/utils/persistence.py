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
    try:
        app_logger.debug(f"Converting data to timestamp: {data}")
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
                app_logger.debug(f"Converted datetime {value} to {result[key]}")
            else:
                result[key] = value
        return result
    except Exception as e:
        app_logger.error(f"Error converting to timestamp: {str(e)}, data: {data}")
        return data

def save_data(data: Any, filename: str) -> None:
    """Save data to a pickle file.
    
    Args:
        data: Data to save
        filename (str): Name of the file to save to
    """
    try:
        app_logger.debug(f"Saving data to {filename}: {data}")
        # Convert any datetime objects to timestamps before saving
        if isinstance(data, dict):
            converted_data = {}
            for k, v in data.items():
                if isinstance(v, dict):
                    try:
                        converted_data[k] = _convert_to_timestamp(v)
                    except Exception as e:
                        app_logger.error(f"Error converting inner dict: {str(e)}, key: {k}, value: {v}")
                        converted_data[k] = v
                else:
                    converted_data[k] = v
            data = converted_data
        
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
            app_logger.debug(f"Loaded data from {filename}: {data}")
            return data
    except Exception as e:
        app_logger.error(f"Failed to load data from {filename}: {str(e)}")
        return default
