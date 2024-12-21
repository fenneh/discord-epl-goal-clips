"""URL handling utilities."""

from urllib.parse import urlparse
from typing import Optional
from src.config.domains import base_domains

def extract_base_domain(url: str) -> Optional[str]:
    """Extract the base domain from a URL.
    
    Args:
        url (str): URL to extract base domain from
        
    Returns:
        str: Full domain, or None if parsing fails
        
    Raises:
        ValueError: If URL is invalid
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not domain:
            domain = parsed.path.lower()
            
        # Invalid URL
        if not domain or '.' not in domain:
            raise ValueError(f"Invalid URL: {url}")
        
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
                # Return the full domain
                return domain
                
        # If no exact match found, try partial matching
        # This helps with cases like 'streamff' matching 'streamff-new'
        for part in parts:
            for base in base_domains:
                if base in part:
                    # Return the full domain
                    return domain
                    
        # For invalid domains, still return the domain
        return domain
    except Exception as e:
        raise ValueError(f"Failed to parse URL: {url}") from e

def is_valid_domain(url: str) -> bool:
    """Check if a URL's domain contains any of our base domains.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if domain is valid, False otherwise
    """
    try:
        domain = extract_base_domain(url)
        if not domain:
            return False
            
        # Check if any of our base domains are in the domain
        return any(base in domain for base in base_domains)
    except ValueError:
        return False

def get_base_domain(url: str) -> str:
    """Get base domain from URL.
    
    Args:
        url (str): URL to parse
        
    Returns:
        str: Base domain (e.g., 'example.com')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Check if domain contains any of our base domains
        for base_domain in base_domains:
            if base_domain in domain:
                return domain
                
        # If no match found, return the full domain
        return domain
        
    except Exception as e:
        return url  # Return original URL if parsing fails
