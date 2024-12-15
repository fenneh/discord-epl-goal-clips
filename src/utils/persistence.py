"""Persistence utilities for storing and retrieving data."""

import pickle
import os
import time
from typing import Set, Dict, Any
from src.utils.logger import app_logger

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
            
            # Convert any datetime objects to timestamps after loading
            if isinstance(data, dict):
                data = {k: _convert_to_timestamp(v) if isinstance(v, dict) else v for k, v in data.items()}
            
            return data
    except Exception as e:
        app_logger.error(f"Failed to load data from {filename}: {str(e)}")
        return default

def _convert_to_timestamp(data: Dict) -> Dict:
    """Convert any datetime objects in the data to timestamps.
    
    Args:
        data (dict): Dictionary that might contain datetime objects
        
    Returns:
        dict: Dictionary with datetime objects converted to timestamps
    """
    if not isinstance(data, dict):
        return data
        
    result = {}
    for k, v in data.items():
        if k == 'timestamp' and hasattr(v, 'timestamp'):
            result[k] = v.timestamp()
        else:
            result[k] = v
    return result
