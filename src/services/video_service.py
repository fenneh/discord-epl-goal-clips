"""Service for extracting video links from various sources."""

import re
import requests
from bs4 import BeautifulSoup
from src.utils.logger import app_logger
from src.config.filters import streamin_domains
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
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

    def validate_mp4_url(self, url: str) -> bool:
        """Validate that an MP4 URL is complete and accessible."""
        try:
            response = requests.head(url, headers=self.headers, allow_redirects=True, timeout=5)
            if response.status_code in [200, 302]:
                return True
            app_logger.debug(f"URL validation failed with status code {response.status_code}: {url}")
            return False
        except Exception as e:
            app_logger.error(f"Error validating URL {url}: {e}")
            return False

    def extract_from_streamff(self, url: str) -> str:
        """Extract MP4 URL from streamff.live."""
        try:
            video_id = url.split('/')[-1]
            if not video_id:
                app_logger.warning(f"Could not extract video ID from URL: {url}")
                return None
                
            mp4_url = f"https://ffedge.streamff.com/uploads/{video_id}.mp4"
            if self.validate_mp4_url(mp4_url):
                app_logger.debug(f"Found MP4 URL: {mp4_url}")
                return mp4_url
                
            app_logger.warning(f"MP4 URL not valid: {mp4_url}")
            return None
            
        except Exception as e:
            app_logger.error(f"Error extracting from streamff: {e}")
            return None

    def extract_from_streamin(self, url: str) -> str:
        """Extract MP4 URL from streamin.one."""
        try:
            app_logger.info(f"Fetching streamin URL: {url}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Use the exact XPath: /html/body/main/div/video/source
            source = soup.select_one('body > main > div > video > source')
            
            if source and source.get('src'):
                mp4_url = source['src']
                app_logger.info(f"Found MP4 URL: {mp4_url}")
                return mp4_url
                
            app_logger.warning("No video source found")
            return None
            
        except Exception as e:
            app_logger.error(f"Error extracting from streamin: {e}")
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
        
        if 'streamable.com' in domain:
            return self.extract_from_streamable(url)
        elif 'streamin.one' in domain or 'streamin.me' in domain:
            return self.extract_from_streamin(url)
        elif 'streamff.com' in domain or 'streamff.live' in domain:
            return self.extract_from_streamff(url)
            
        app_logger.warning(f"Unsupported domain for MP4 extraction: {domain}")
        return None

# Create a global instance
video_extractor = VideoExtractor()
