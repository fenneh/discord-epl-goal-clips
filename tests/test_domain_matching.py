"""Test domain matching with different TLDs."""

import pytest
from src.utils.url_utils import extract_base_domain, is_valid_domain

# Test URLs with different TLDs and formats
test_urls = [
    # Standard cases
    ('https://streamff.com/v/123456', True, 'streamff.com'),
    ('https://streamff.live/v/123456', True, 'streamff.live'),
    ('https://streamff.london/v/123456', True, 'streamff.london'),
    ('https://streamff-new.com/v/123456', True, 'streamff-new.com'),
    ('https://new-streamff.com/v/123456', True, 'new-streamff.com'),
    
    # Other domains
    ('https://streamja.com/video/123', True, 'streamja.com'),
    ('https://streamja.live/video/123', True, 'streamja.live'),
    ('https://streamja-cdn.net/video/123', True, 'streamja-cdn.net'),
    
    ('https://streamable.com/123456', True, 'streamable.com'),
    ('https://streamable.io/123456', True, 'streamable.io'),
    ('https://streamable-cdn.net/123456', True, 'streamable-cdn.net'),
    
    # Invalid cases
    ('https://example.com/video', False, 'example.com'),
    ('https://invalid-domain.com/123', False, 'invalid-domain.com'),
    ('not-a-url', False, None)
]

@pytest.mark.parametrize("url,is_valid,expected_domain", test_urls)
def test_domain_matching(url, is_valid, expected_domain):
    """Test domain matching for various URLs."""
    # Test domain validation
    assert is_valid_domain(url) == is_valid
    
    # Test domain extraction
    if expected_domain:
        assert extract_base_domain(url) == expected_domain
    else:
        with pytest.raises(ValueError):
            extract_base_domain(url)
