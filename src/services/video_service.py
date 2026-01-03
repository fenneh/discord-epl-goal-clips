"""Service for extracting video links from various sources."""

import asyncio
import re
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from src.utils.logger import app_logger


class VideoExtractor:
    """Extracts video links from various hosting sites."""

    def __init__(self):
        """Initialize the video extractor."""
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Returns a shared aiohttp client session."""
        return aiohttp.ClientSession(headers=self.headers)

    async def validate_mp4_url(self, session: aiohttp.ClientSession, url: str) -> bool:
        """Validate that an MP4 URL is accessible."""
        try:
            app_logger.info(f"Validating MP4 URL: {url}")
            async with asyncio.timeout(10):
                async with session.head(url, allow_redirects=True) as response:
                    if response.history:
                        redirect_chain = " -> ".join(
                            str(r.url) for r in response.history
                        )
                        app_logger.info(
                            f"Followed redirects: {redirect_chain} -> {response.url}"
                        )

                    app_logger.info(
                        f"Response: {response.status} {response.content_type}"
                    )

                    if 200 <= response.status < 300:
                        content_type = response.content_type or ""
                        valid_types = ["video", "mp4", "octet-stream"]
                        if any(t in content_type for t in valid_types):
                            app_logger.info(f"Valid MP4 URL: {response.url}")
                            return True

                    app_logger.warning(
                        f"URL validation failed - Status: {response.status}, "
                        f"Content-Type: {response.content_type}"
                    )
                    return False

        except asyncio.TimeoutError:
            app_logger.error(f"Timeout error validating URL {url}")
            return False
        except aiohttp.ClientError as e:
            # More specific catch for network/HTTP related errors
            app_logger.error(f"ClientError validating URL {url}: {str(e)}")
            return False
        except Exception as e:
            app_logger.error(
                f"Unexpected error validating URL {url}: {str(e)}", exc_info=True
            )
            return False

    async def extract_from_streamff(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """Extract MP4 URL from streamff sites."""
        try:
            app_logger.info(f"Extracting from streamff URL: {url}")

            # Extract video ID from URL
            video_id = url.split("/v/")[-1] if "/v/" in url else url.split("/")[-1]
            app_logger.info(f"Extracted video ID: {video_id}")

            # Try multiple CDN URLs (new CDN first, then old as fallback)
            cdn_urls = [
                f"https://cdn.streamff.one/{video_id}.mp4",
                f"https://ffedge.streamff.com/uploads/{video_id}.mp4",
            ]

            for mp4_url in cdn_urls:
                app_logger.info(f"Trying MP4 URL: {mp4_url}")
                if await self.validate_mp4_url(session, mp4_url):
                    app_logger.info(f"Found valid MP4 URL: {mp4_url}")
                    return mp4_url

            # Fallback to page parsing
            app_logger.info("Direct CDN URLs failed, trying page parsing")
            return await self._extract_from_page(session, url)

        except Exception as e:
            app_logger.error(f"Error extracting from streamff: {e}", exc_info=True)
            return None

    async def extract_from_streamin(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """Extract MP4 URL from streamin sites."""
        try:
            # Extract video ID from URL
            video_id = url.split("/")[-1]

            # Try different domain variations for MP4
            domains = ["https://streamin.fun/uploads/", "https://streamin.me/uploads/"]

            for domain in domains:
                mp4_url = f"{domain}{video_id}.mp4"
                app_logger.info(f"Trying MP4 URL: {mp4_url}")

                if await self.validate_mp4_url(session, mp4_url):
                    return mp4_url

            # If direct URLs don't work, try page parsing
            return await self._extract_from_page(session, url)

        except asyncio.TimeoutError:
            app_logger.error(f"Timeout error fetching streamin URL {url}")
            return None
        except aiohttp.ClientError as e:
            app_logger.error(f"ClientError extracting from streamin {url}: {str(e)}")
            return None
        except Exception as e:
            app_logger.error(
                f"Unexpected error extracting from streamin: {e}", exc_info=True
            )
            return None

    async def _extract_from_page(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """Extract MP4 URL by parsing the page content."""
        try:
            headers = {**self.headers, "Referer": url}
            app_logger.info(f"Fetching page: {url}")

            async with asyncio.timeout(15):
                async with session.get(
                    url, headers=headers, allow_redirects=True
                ) as response:
                    response.raise_for_status()
                    content = await response.text()
                    soup = BeautifulSoup(content, "html.parser")

                    # Try meta tags first
                    for prop in ["og:video:secure_url", "og:video"]:
                        meta = soup.find("meta", {"property": prop})
                        if meta and meta.get("content"):
                            mp4_url = meta["content"]
                            app_logger.info(f"Found MP4 URL in {prop}: {mp4_url}")
                            if await self.validate_mp4_url(session, mp4_url):
                                return mp4_url
                            app_logger.warning(f"{prop} validation failed: {mp4_url}")

                    # Try video source elements
                    selectors = ["body > main > div > video > source", "video > source"]
                    for selector in selectors:
                        source = soup.select_one(selector)
                        if source and source.get("src"):
                            src = source["src"]
                            if await self.validate_mp4_url(session, src):
                                return src

                    return None

        except Exception as e:
            app_logger.error(f"Error extracting from page {url}: {e}", exc_info=True)
            return None

    async def extract_from_dubz(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """Extract MP4 URL from dubz sites."""
        try:
            video_id = url.split("/")[-1]
            mp4_url = f"https://cdn.squeelab.com/guest/videos/{video_id}.mp4"
            if await self.validate_mp4_url(session, mp4_url):
                return mp4_url
            app_logger.warning("No valid MP4 URL found for dubz")
            return None
        except Exception as e:
            app_logger.error(f"Error extracting from dubz: {e}", exc_info=True)
            return None

    async def extract_from_streamable(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """Extract MP4 URL from streamable sites."""
        try:
            app_logger.info(f"Fetching streamable URL: {url}")
            async with asyncio.timeout(15):
                async with session.get(url) as response:
                    response.raise_for_status()
                    content = await response.text()
                    soup = BeautifulSoup(content, "html.parser")

                    # Find video source element
                    selectors = ["video source", "main div video source"]

                    for selector in selectors:
                        source = soup.select_one(selector)
                        if source and source.get("src"):
                            mp4_url = self._clean_streamable_url(source["src"])
                            if await self.validate_mp4_url(session, mp4_url):
                                return mp4_url

                    # Fallback to any source element
                    source = soup.find("source")
                    if source and source.get("src"):
                        mp4_url = self._clean_streamable_url(source["src"])
                        if await self.validate_mp4_url(session, mp4_url):
                            return mp4_url

                    return None

        except asyncio.TimeoutError:
            app_logger.error(f"Timeout error fetching streamable URL {url}")
            return None
        except aiohttp.ClientError as e:
            app_logger.error(f"ClientError extracting from streamable {url}: {e}")
            return None
        except Exception as e:
            app_logger.error(
                f"Unexpected error extracting from streamable: {e}", exc_info=True
            )
            return None

    def _clean_streamable_url(self, url: str) -> str:
        """Clean streamable URL by removing fragments and fixing protocol."""
        if "#t=" in url:
            url = url.split("#")[0]
        if url.startswith("//"):
            url = f"https:{url}"
        return url

    async def extract_mp4_url(self, url: str) -> Optional[str]:
        """Extract MP4 URL from supported sites."""
        if not url:
            return None

        # Ensure URL has proper scheme
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
            app_logger.info(f"Added scheme to URL: {url}")

        async with await self._get_session() as session:
            try:
                # Dispatch to appropriate extractor based on domain
                extractors = {
                    "streamff": self.extract_from_streamff,
                    "streamin": self.extract_from_streamin,
                    "dubz": self.extract_from_dubz,
                    "streamable": self.extract_from_streamable,
                }

                for domain, extractor in extractors.items():
                    if re.search(rf"https://[^/]*{domain}\.\w+", url, re.IGNORECASE):
                        app_logger.info(f"Using {domain} extractor for: {url}")
                        return await extractor(session, url)

                app_logger.warning(f"No extractor found for URL: {url}")
                return None

            except aiohttp.ClientError as e:
                app_logger.error(f"ClientError extracting from {url}: {e}")
                return None
            except asyncio.TimeoutError:
                app_logger.error(f"Timeout extracting from {url}")
                return None
            except Exception as e:
                app_logger.error(
                    f"Unexpected error extracting from {url}: {e}", exc_info=True
                )
                return None


# Create a single instance of the extractor
video_extractor = VideoExtractor()
