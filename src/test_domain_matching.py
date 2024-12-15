"""Test domain matching with different TLDs."""

from src.utils.url_utils import extract_base_domain, is_valid_domain

# Test URLs with different TLDs and formats
test_urls = [
    # Standard cases
    'https://streamff.com/v/123456',
    'https://streamff.live/v/123456',
    'https://streamff.london/v/123456',
    'https://streamff-new.com/v/123456',
    'https://new-streamff.com/v/123456',
    
    # Other domains
    'https://streamja.com/video/123',
    'https://streamja.live/video/123',
    'https://streamja-cdn.net/video/123',
    
    'https://streamable.com/123456',
    'https://streamable.io/123456',
    'https://streamable-cdn.net/123456',
    
    # Invalid cases
    'https://example.com/video',
    'https://invalid-domain.com/123',
    'not-a-url'
]

def main():
    print("Testing domain matching...")
    print("-" * 50)
    
    for url in test_urls:
        base = extract_base_domain(url)
        valid = is_valid_domain(url)
        print(f"\nURL: {url}")
        print(f"Base domain: {base}")
        print(f"Valid: {valid}")
        
if __name__ == "__main__":
    main()
