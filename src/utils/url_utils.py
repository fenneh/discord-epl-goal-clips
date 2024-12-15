"""URL handling utilities."""

from urllib.parse import urlparse
from typing import Optional
from src.config.domains import base_domains

def extract_base_domain(url: str) -> Optional[str]:
    """Extract the base domain from a URL without TLD.
    
    Args:
        url (str): URL to extract base domain from
        
    Returns:
        str: Base domain without TLD, or None if parsing fails
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            domain = parsed.path.lower()
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
            
        # Split by dots and get the domain parts
        parts = domain.split('.')
        
        # Try to find a matching base domain in our parts
        for part in parts:
            if part in base_domains:
                return part
                
        # If no exact match found, try partial matching
        # This helps with cases like 'streamff' matching 'streamff-new'
        for part in parts:
            for base in base_domains:
                if base in part:
                    return base
                    
        return None
    except Exception:
        return None

def is_valid_domain(url: str) -> bool:
    """Check if a URL's domain contains any of our base domains.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if domain is valid, False otherwise
    """
    base = extract_base_domain(url)
    return base is not None
