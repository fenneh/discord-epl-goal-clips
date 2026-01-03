"""URL handling utilities."""

from urllib.parse import urlparse
from typing import Optional, Dict

# Use the base_domains set from filters as the source of truth
from src.config.filters import base_domains
from src.utils.logger import app_logger

# Removed extract_base_domain and is_valid_domain as they were overlapping/confusing


def get_domain_info(url: str) -> Optional[Dict[str, Optional[str]]]:
    """Parse URL, normalize domain, and check if it matches known video base domains.

    Args:
        url (str): URL to parse.

    Returns:
        Optional[Dict[str, Optional[str]]]:
            A dictionary containing 'full_domain' (normalized) and 'matched_base'
            (e.g., 'streamable') if a known base domain is found within the full domain.
            Returns None if the URL is invalid or parsing fails.
    """
    if not url or not isinstance(url, str):
        app_logger.warning(f"Invalid URL received for domain check: {url}")
        return None

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Handle cases where domain might be in path (e.g., for file:// URLs, though unlikely here)
        if not domain and parsed.path:
            # Attempt to extract something resembling a domain from the path
            path_parts = parsed.path.lower().split("/")
            if len(path_parts) > 1 and "." in path_parts[0]:
                domain = path_parts[0]
            else:
                app_logger.debug(f"Could not extract domain from netloc or path: {url}")
                return None  # Cannot determine domain
        elif not domain:
            app_logger.debug(f"Could not extract domain from netloc: {url}")
            return None  # Cannot determine domain

        # Remove 'www.' prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        # Check if domain contains any of our base domains
        matched_base = None
        for base in base_domains:
            if base in domain:
                matched_base = base
                break  # Found the first match

        return {"full_domain": domain, "matched_base": matched_base}

    except Exception as e:
        app_logger.error(
            f"Error parsing URL '{url}' in get_domain_info: {e}", exc_info=True
        )
        return None  # Return None on parsing errors


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
        if domain.startswith("www."):
            domain = domain[4:]

        # Check if domain contains any of our base domains
        for base_domain in base_domains:
            if base_domain in domain:
                return domain

        # If no match found, return the full domain
        return domain

    except Exception:
        return url  # Return original URL if parsing fails
