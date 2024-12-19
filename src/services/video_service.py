"""Service for extracting video links from various sources."""

import re
import requests
from bs4 import BeautifulSoup
from src.utils.logger import app_logger
from src.config.filters import base_domains
from typing import Optional
from urllib.parse import urlparse

class VideoExtractor:
    """Video extractor class for handling various video hosting sites."""
    
    def __init__(self):
        """Initialize the video extractor."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://streamin.one/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }

    def validate_mp4_url(self, url: str) -> bool:
        """Validate that an MP4 URL is complete and accessible."""
        try:
            app_logger.info(f"Validating MP4 URL: {url}")
            response = requests.head(url, headers=self.headers, allow_redirects=True, timeout=5)
            app_logger.info(f"Got response: {response.status_code} {response.headers.get('Content-Type', '')}")
            
            # Accept any 2xx status code and check content type
            if 200 <= response.status_code < 300:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'video' in content_type or 'mp4' in content_type:
                    app_logger.info(f"Valid MP4 URL found: {url}")
                    return True
                    
            app_logger.warning(f"URL validation failed - Status: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
            return False
            
        except Exception as e:
            app_logger.error(f"Error validating URL {url}: {str(e)}")
            return False

    def extract_from_streamff(self, url: str) -> str:
        """Extract MP4 URL from streamff.live."""
        try:
            app_logger.info(f"Extracting from streamff URL: {url}")
            video_id = url.split('/')[-1]
            if not video_id:
                app_logger.warning(f"Could not extract video ID from URL: {url}")
                return None
                
            # Try both edge and regular domains
            domains = [
                "https://ffedge.streamff.com/uploads",
                "https://streamff.com/uploads"
            ]
            
            for domain in domains:
                mp4_url = f"{domain}/{video_id}.mp4"
                app_logger.info(f"Trying MP4 URL: {mp4_url}")
                if self.validate_mp4_url(mp4_url):
                    app_logger.info(f"Found valid MP4 URL: {mp4_url}")
                    return mp4_url
                    
            app_logger.warning(f"No valid MP4 URL found for video ID: {video_id}")
            return None
            
        except Exception as e:
            app_logger.error(f"Error extracting from streamff: {str(e)}")
            return None

    def extract_from_streamin(self, url: str) -> str:
        """Extract MP4 URL from streamin.one."""
        try:
            app_logger.info(f"Fetching streamin URL: {url}")
            
            # Update headers to better mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://streamin.one/',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            app_logger.info("Making request with headers:")
            for k, v in headers.items():
                app_logger.info(f"{k}: {v}")
            
            response = requests.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()
            
            app_logger.info(f"Got response from {response.url}")
            app_logger.info(f"Response status: {response.status_code}")
            app_logger.info("Response headers:")
            for k, v in response.headers.items():
                app_logger.info(f"{k}: {v}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            app_logger.info("Looking for video URL in meta tags...")
            
            # Log all meta tags for debugging
            app_logger.info("All meta tags:")
            for meta in soup.find_all('meta'):
                app_logger.info(str(meta))
            
            # First try og:video:secure_url meta tag
            meta = soup.find('meta', {'property': 'og:video:secure_url'})
            if meta and meta.get('content'):
                mp4_url = meta['content']
                app_logger.info(f"Found MP4 URL in og:video:secure_url: {mp4_url}")
                return mp4_url
                
            # Then try og:video meta tag
            meta = soup.find('meta', {'property': 'og:video'})
            if meta and meta.get('content'):
                mp4_url = meta['content']
                app_logger.info(f"Found MP4 URL in og:video: {mp4_url}")
                return mp4_url
                
            # If meta tags not found, try video source
            app_logger.info("Looking for video source...")
            source = soup.select_one('body > main > div > video > source')
            if source:
                app_logger.info(f"Found video source tag: {source}")
                src = source.get('src')
                if src:
                    app_logger.info(f"Found MP4 URL in video source: {src}")
                    return src
            
            app_logger.warning("No video source found")
            # Log a sample of the HTML for debugging
            app_logger.info("Sample of HTML content:")
            app_logger.info(response.text[:1000])
            return None
            
        except Exception as e:
            app_logger.error(f"Error extracting from streamin: {str(e)}")
            app_logger.error("Stack trace:", exc_info=True)
            return None

    def extract_from_dubz(self, url: str) -> str:
        """Extract MP4 URL from dubz.link."""
        try:
            video_id = url.split('/')[-1]
            mp4_url = f"https://cdn.squeelab.com/guest/videos/{video_id}.mp4"
            if self.validate_mp4_url(mp4_url):
                return mp4_url
            return None
        except Exception as e:
            app_logger.error(f"Error extracting from dubz: {e}")
            return None

    def extract_from_streamable(self, url: str) -> str:
        """Extract MP4 URL from streamable.com."""
        try:
            app_logger.info(f"Fetching streamable URL: {url}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            app_logger.info("Looking for video source tag...")
            
            # Try different selectors
            source = soup.select_one('video source')
            if not source:
                app_logger.info("No source found with 'video source', trying 'main div video source'")
                source = soup.select_one('main div video source')
            if not source:
                app_logger.info("No source found with selectors, trying find('source')")
                source = soup.find('source')
                
            if source:
                app_logger.info(f"Found source tag: {source}")
                if source.get('src'):
                    mp4_url = source['src']
                    app_logger.info(f"Found src attribute: {mp4_url}")
                    # Keep all query parameters but remove the #t=0.1 fragment
                    if '#t=' in mp4_url:
                        mp4_url = mp4_url.split('#')[0]
                        
                    if self.validate_mp4_url(mp4_url):
                        app_logger.info(f"Successfully validated MP4 URL: {mp4_url}")
                        return mp4_url
                    else:
                        app_logger.warning(f"MP4 URL validation failed: {mp4_url}")
                else:
                    app_logger.warning("Source tag found but no src attribute")
            else:
                app_logger.warning("No source tag found in page")
                
            # Let's log the HTML to see what we're dealing with
            app_logger.info("Page HTML structure:")
            app_logger.info(soup.prettify()[:1000])  # First 1000 chars to avoid spam
            
            return None
            
        except Exception as e:
            app_logger.error(f"Error extracting from streamable: {e}")
            return None

    def extract_mp4_url(self, url: str) -> Optional[str]:
        """Extract MP4 URL from any supported domain."""
        domain = urlparse(url).netloc.lower()
        
        # Check if any base domain is in the full domain
        supported = False
        for base in base_domains:
            if base in domain:
                supported = True
                break
                
        if not supported:
            app_logger.warning(f"Unsupported domain for MP4 extraction: {domain}")
            return None
            
        if 'streamable' in domain:
            return self.extract_from_streamable(url)
        elif 'streamin' in domain:  # Handles all streamin variants
            return self.extract_from_streamin(url)
        elif 'streamff' in domain:  # Handles all streamff variants
            return self.extract_from_streamff(url)
        elif 'dubz' in domain:
            return self.extract_from_dubz(url)
            
        app_logger.warning(f"No extractor found for supported domain: {domain}")
        return None

# Create a global instance
video_extractor = VideoExtractor()
