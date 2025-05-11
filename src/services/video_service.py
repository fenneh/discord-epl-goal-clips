"""Service for extracting video links from various sources."""

import re
# import requests # No longer needed
import aiohttp # Use asynchronous HTTP client
import asyncio # For potential timeouts
from bs4 import BeautifulSoup
from src.utils.logger import app_logger
# Use base_domains from filters config
from src.config.filters import base_domains 
from typing import Optional, Dict
from urllib.parse import urlparse
import traceback

class VideoExtractor:
    """Video extractor class for handling various video hosting sites asynchronously."""
    
    def __init__(self):
        """Initialize the video extractor."""
        # Define headers once
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
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        }
        # Session is managed per extraction call now
        # self.session = None 

    async def _get_session(self) -> aiohttp.ClientSession:
        """Returns a shared aiohttp client session."""
        # Simple approach: create a new session each time. 
        # For higher performance, consider managing a single session 
        # within the application's lifespan or using a context manager.
        return aiohttp.ClientSession(headers=self.headers)

    async def validate_mp4_url(self, session: aiohttp.ClientSession, url: str) -> bool:
        """Validate that an MP4 URL is complete and accessible asynchronously."""
        try:
            app_logger.info(f"Validating MP4 URL: {url}")
            # Use asyncio.timeout for request timeout
            async with asyncio.timeout(10):
                async with session.head(url, allow_redirects=True) as response:
                    # Log redirect chain if any
                    if len(response.history) > 0:
                        app_logger.info(f"Followed redirects: {' -> '.join(str(r.url) for r in response.history)} -> {response.url}")
                    
                    app_logger.info(f"Got response: {response.status} {response.content_type}")
                    
                    # Accept any 2xx status code and check content type
                    if 200 <= response.status < 300:
                        content_type = response.content_type or ''
                        if any(t in content_type for t in ['video', 'mp4', 'octet-stream']):
                            app_logger.info(f"Valid MP4 URL found: {response.url}")
                            return True
                            
                    app_logger.warning(f"URL validation failed - Status: {response.status}, Content-Type: {response.content_type}")
                    return False
            
        except asyncio.TimeoutError:
             app_logger.error(f"Timeout error validating URL {url}")
             return False
        except aiohttp.ClientError as e:
            # More specific catch for network/HTTP related errors
            app_logger.error(f"ClientError validating URL {url}: {str(e)}")
            return False
        except Exception as e:
            app_logger.error(f"Unexpected error validating URL {url}: {str(e)}", exc_info=True)
            return False

    async def extract_from_streamff(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Extract MP4 URL from streamff.live asynchronously."""
        try:
            app_logger.info(f"Extracting from streamff URL: {url}")
            
            # Handle both streamff.com and streamff.live URLs
            if '/v/' in url:
                video_id = url.split('/v/')[-1]
            else:
                video_id = url.split('/')[-1]
                
            app_logger.info(f"Extracted video ID: {video_id}")
            
            # Try direct MP4 URL
            mp4_url = f"https://ffedge.streamff.com/uploads/{video_id}.mp4"
            app_logger.info(f"Trying MP4 URL: {mp4_url}")
            
            if await self.validate_mp4_url(session, mp4_url):
                app_logger.info(f"Found valid MP4 URL: {mp4_url}")
                return mp4_url
                
            app_logger.warning("No valid MP4 URL found for streamff")
            return None
            
        except Exception as e:
            app_logger.error(f"Error extracting from streamff: {str(e)}", exc_info=True)
            return None

    async def extract_from_streamin(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Extract MP4 URL from streamin.one/streamin.me asynchronously."""
        try:
            # Extract video ID from URL
            video_id = url.split('/')[-1]
            
            # Try different domain variations for MP4
            mp4_domains = [
                "https://streamin.fun/uploads/",
                "https://streamin.me/uploads/"
            ]
            
            for domain in mp4_domains:
                mp4_url = f"{domain}{video_id}.mp4"
                app_logger.info(f"Trying MP4 URL: {mp4_url}")
                
                # Validate the URL
                if await self.validate_mp4_url(session, mp4_url):
                    return mp4_url
                
            # If direct URLs don't work, try page parsing
            page_headers = {**self.headers, 'Referer': url}
            app_logger.info(f"Fetching streamin URL: {url}")
            
            # app_logger.info("Making request with headers:")
            # for k, v in page_headers.items():
            #     app_logger.info(f"{k}: {v}")
            
            async with asyncio.timeout(15):
                 async with session.get(url, headers=page_headers, allow_redirects=True) as response:
                    response.raise_for_status() # Raise exception for bad status codes
                    
                    app_logger.info(f"Got response from {response.url}")
                    app_logger.info(f"Response status: {response.status}")
                    # app_logger.info("Response headers:")
                    # for k, v in response.headers.items():
                    #     app_logger.info(f"{k}: {v}")

                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    app_logger.info("Looking for video URL in meta tags...")
                    
                    # Log all meta tags for debugging
                    # app_logger.info("All meta tags:")
                    # for meta in soup.find_all('meta'):
                    #     app_logger.info(str(meta))
                    
                    # First try og:video:secure_url meta tag
                    meta = soup.find('meta', {'property': 'og:video:secure_url'})
                    if meta and meta.get('content'):
                        mp4_url = meta['content']
                        app_logger.info(f"Found MP4 URL in og:video:secure_url: {mp4_url}")
                        # Validate before returning
                        if await self.validate_mp4_url(session, mp4_url):
                             return mp4_url
                        else:
                             app_logger.warning(f"og:video:secure_url found but failed validation: {mp4_url}")
                        
                    # Then try og:video meta tag
                    meta = soup.find('meta', {'property': 'og:video'})
                    if meta and meta.get('content'):
                        mp4_url = meta['content']
                        app_logger.info(f"Found MP4 URL in og:video: {mp4_url}")
                        # Validate before returning
                        if await self.validate_mp4_url(session, mp4_url):
                            return mp4_url
                        else:
                             app_logger.warning(f"og:video found but failed validation: {mp4_url}")
                        
                    # If meta tags not found, try video source
                    app_logger.info("Looking for video source...")
                    source = soup.select_one('body > main > div > video > source') # More specific selector
                    if not source:
                         source = soup.select_one('video > source') # Less specific
                    if source:
                        app_logger.info(f"Found video source tag: {source}")
                        src = source.get('src')
                        if src:
                            app_logger.info(f"Found MP4 URL in video source: {src}")
                            # Validate before returning
                            if await self.validate_mp4_url(session, src):
                                 return src
                            else:
                                 app_logger.warning(f"Video source found but failed validation: {src}")
                    
                    app_logger.warning("No valid video source found via meta or source tags for streamin")
                    # Log a sample of the HTML for debugging
                    # app_logger.info("Sample of HTML content:")
                    # app_logger.info(html_content[:1000])
                    return None

        except asyncio.TimeoutError:
             app_logger.error(f"Timeout error fetching streamin URL {url}")
             return None        
        except aiohttp.ClientError as e:
            app_logger.error(f"ClientError extracting from streamin {url}: {str(e)}")
            return None
        except Exception as e:
            app_logger.error(f"Unexpected error extracting from streamin: {str(e)}", exc_info=True)
            return None

    async def extract_from_dubz(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Extract MP4 URL from dubz.link asynchronously."""
        try:
            video_id = url.split('/')[-1]
            mp4_url = f"https://cdn.squeelab.com/guest/videos/{video_id}.mp4"
            if await self.validate_mp4_url(session, mp4_url):
                return mp4_url
            app_logger.warning("No valid MP4 URL found for dubz")
            return None
        except Exception as e:
            app_logger.error(f"Error extracting from dubz: {e}", exc_info=True)
            return None

    async def extract_from_streamable(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Extract MP4 URL from streamable.com asynchronously."""
        try:
            app_logger.info(f"Fetching streamable URL: {url}")
            async with asyncio.timeout(15):
                async with session.get(url) as response: # Use session headers by default
                    response.raise_for_status()
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')
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
                            
                            # Streamable URLs often start with //, prepend https:
                            if mp4_url.startswith('//'):
                                mp4_url = f"https:{mp4_url}"

                            if await self.validate_mp4_url(session, mp4_url):
                                app_logger.info(f"Successfully validated MP4 URL: {mp4_url}")
                                return mp4_url
                            else:
                                app_logger.warning(f"MP4 URL validation failed: {mp4_url}")
                        else:
                            app_logger.warning("Source tag found but no src attribute")
                    else:
                        app_logger.warning("No source tag found in page")
                        
                    # Log the HTML to see what we're dealing with if needed
                    # app_logger.info("Page HTML structure:")
                    # app_logger.info(soup.prettify()[:1000])
                    
                    return None

        except asyncio.TimeoutError:
             app_logger.error(f"Timeout error fetching streamable URL {url}")
             return None        
        except aiohttp.ClientError as e:
            app_logger.error(f"ClientError extracting from streamable {url}: {str(e)}")
            return None
        except Exception as e:
            app_logger.error(f"Unexpected error extracting from streamable: {e}", exc_info=True)
            return None

    # Add any other site-specific extractors here
    # Example:
    # async def extract_from_anothersite(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
    #     # ... extraction logic ...
    #     pass

    async def extract_mp4_url(self, url: str) -> Optional[str]:
        """Extract MP4 URL from supported sites by dispatching to the correct method asynchronously."""
        if not url:
            return None

        # Get a new session for this extraction attempt
        # This ensures headers are fresh if they were modified by a previous call
        # and simplifies session management for this specific class structure.
        # For very high-frequency calls, a shared session within app lifespan might be better.
        async with await self._get_session() as session:
            try:
                # Ensure URL has a scheme
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                    app_logger.info(f"Added scheme to URL: {url}")

                # Use regex for flexible TLD matching and dispatch
                # The order matters if a URL could potentially match multiple patterns.
                if re.search(r'https://[^/]*streamff\.\w+', url, re.IGNORECASE):
                    app_logger.info(f"Dispatching to streamff extractor for: {url}")
                    return await self.extract_from_streamff(session, url)
                elif re.search(r'https://[^/]*streamin\.\w+', url, re.IGNORECASE):
                    app_logger.info(f"Dispatching to streamin extractor for: {url}")
                    return await self.extract_from_streamin(session, url)
                elif re.search(r'https://[^/]*dubz\.\w+', url, re.IGNORECASE):
                    app_logger.info(f"Dispatching to dubz extractor for: {url}")
                    return await self.extract_from_dubz(session, url)
                elif re.search(r'https://[^/]*streamable\.\w+', url, re.IGNORECASE):
                    app_logger.info(f"Dispatching to streamable extractor for: {url}")
                    return await self.extract_from_streamable(session, url)
                # Add other site checks here using re.search with their base domain names
                # elif re.search(r'https://[^/]*anothersite\.\w+', url, re.IGNORECASE):
                #     return await self.extract_from_anothersite(session, url)
                else:
                    app_logger.warning(f"No specific extractor found for URL: {url}")
                    # Fallback: try a generic scrape if desired, or just return None
                    # For now, we only use specific extractors.
                    return None
            except aiohttp.ClientError as e:
                app_logger.error(f"ClientError during MP4 extraction dispatch for {url}: {str(e)}")
                return None
            except asyncio.TimeoutError:
                app_logger.error(f"Timeout during MP4 extraction dispatch for {url}")
                return None
            except Exception as e:
                app_logger.error(f"Unexpected error in extract_mp4_url for {url}: {str(e)}", exc_info=True)
                return None

# Create a single instance of the extractor
video_extractor = VideoExtractor()
