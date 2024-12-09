import os
import praw
import re
import requests
import time
import pickle
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
from difflib import SequenceMatcher
import argparse
from threading import Thread
import uvicorn
from fastapi import FastAPI
import asyncio

# Configure main logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configure separate logger for failed extractions
failed_extractions_logger = logging.getLogger('failed_extractions')
failed_extractions_logger.setLevel(logging.INFO)
failed_handler = logging.FileHandler('failed_extractions.log')
failed_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
failed_extractions_logger.addHandler(failed_handler)

# Load environment variables from .env file
load_dotenv()

# Read secrets from environment variables
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
DISCORD_USERNAME = os.getenv('DISCORD_USERNAME', 'Ally')  # Default to 'Ally' if not set
DISCORD_AVATAR_URL = os.getenv('DISCORD_AVATAR_URL', 'https://cdn1.rangersnews.uk/uploads/24/2024/03/GettyImages-459578698-scaled-e1709282146939-1024x702.jpg')  # Default to current image if not set

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

# Keywords to identify goal posts
goal_keywords = [
    "goal", 
    "scores", 
    "scored", 
    r"\d{1,3}'",  # Matches minute markers like 45'
    r"\[\d+\]\s*-\s*\d+",  # Matches [5] - 2
    r"\d+\s*-\s*\[\d+\]",  # Matches 2 - [5]
]

# Specific websites to match URLs
streamin_domains = ["streamin.one", "streamin.me", "streamin.pro", "streamin.live", "streamin.cc", "streamin.xyz"]
specific_sites = ["streamff.co"] + streamin_domains + ["dubz.link"]

# Premier League teams and their aliases
premier_league_teams = {
    "Arsenal": {
        "names": ["Arsenal", "The Arsenal", "The Gunners"],
        "color": 0xFF0000,  # Red
        "logo": "https://resources.premierleague.com/premierleague/badges/t3.png"
    },
    "Aston Villa": {
        "names": ["Aston Villa", "Villa"],
        "color": 0x95BFE5,  # Claret
        "logo": "https://resources.premierleague.com/premierleague/badges/t7.png"
    },
    "Bournemouth": {
        "names": ["Bournemouth", "AFC Bournemouth", "The Cherries"],
        "color": 0xDA291C,  # Red
        "logo": "https://resources.premierleague.com/premierleague/badges/t91.png"
    },
    "Brentford": {
        "names": ["Brentford", "The Bees"],
        "color": 0xE30613,  # Red
        "logo": "https://resources.premierleague.com/premierleague/badges/t94.png"
    },
    "Brighton": {
        "names": ["Brighton", "Brighton & Hove Albion", "Brighton and Hove Albion", "The Seagulls"],
        "color": 0x0057B8,  # Blue
        "logo": "https://resources.premierleague.com/premierleague/badges/t36.png"
    },
    "Chelsea": {
        "names": ["Chelsea", "The Blues"],
        "color": 0x034694,  # Blue
        "logo": "https://resources.premierleague.com/premierleague/badges/t8.png"
    },
    "Crystal Palace": {
        "names": ["Crystal Palace", "Palace", "The Eagles"],
        "color": 0x1B458F,  # Blue
        "logo": "https://resources.premierleague.com/premierleague/badges/t31.png"
    },
    "Everton": {
        "names": ["Everton", "The Toffees"],
        "color": 0x003399,  # Blue
        "logo": "https://resources.premierleague.com/premierleague/badges/t11.png"
    },
    "Fulham": {
        "names": ["Fulham", "The Cottagers"],
        "color": 0xFFFFFF,  # White
        "logo": "https://resources.premierleague.com/premierleague/badges/t54.png"
    },
    "Liverpool": {
        "names": ["Liverpool", "The Reds"],
        "color": 0xC8102E,  # Red
        "logo": "https://resources.premierleague.com/premierleague/badges/t14.png"
    },
    "Manchester City": {
        "names": ["Manchester City", "Man City"],
        "color": 0x6CABDD,  # Sky Blue
        "logo": "https://resources.premierleague.com/premierleague/badges/t43.png"
    },
    "Manchester United": {
        "names": ["Manchester United", "Man United", "Man Utd"],
        "color": 0xDA291C,  # Red
        "logo": "https://resources.premierleague.com/premierleague/badges/t1.png"
    },
    "Newcastle United": {
        "names": ["Newcastle United", "Newcastle", "The Magpies"],
        "color": 0x241F20,  # Black
        "logo": "https://resources.premierleague.com/premierleague/badges/t4.png"
    },
    "Nottingham Forest": {
        "names": ["Nottingham Forest", "Forest"],
        "color": 0xDD0000,  # Red
        "logo": "https://resources.premierleague.com/premierleague/badges/t17.png"
    },
    "Tottenham": {
        "names": ["Tottenham", "Tottenham Hotspur", "Spurs"],
        "color": 0x132257,  # Navy
        "logo": "https://resources.premierleague.com/premierleague/badges/t6.png"
    },
    "West Ham": {
        "names": ["West Ham", "West Ham United", "The Hammers"],
        "color": 0x7A263A,  # Claret
        "logo": "https://resources.premierleague.com/premierleague/badges/t21.png"
    },
    "Wolves": {
        "names": ["Wolves", "Wolverhampton", "Wolverhampton Wanderers"],
        "color": 0xFDB913,  # Gold
        "logo": "https://resources.premierleague.com/premierleague/badges/t39.png"
    }
}

# Feature toggle for finding direct MP4 links
FIND_MP4_LINKS = True

# Set to keep track of posted URLs and scores
posted_urls = set()
posted_scores = {}

# File paths for persistence
POSTED_URLS_FILE = 'posted_urls.pkl'
POSTED_SCORES_FILE = 'posted_scores.pkl'

# Add at the top level with other global variables
mp4_retry_posts = set()

def load_history():
    """Load the history of posted URLs and scores from disk."""
    global posted_urls, posted_scores
    try:
        with open(POSTED_URLS_FILE, 'rb') as f:
            posted_urls = pickle.load(f)
    except FileNotFoundError:
        posted_urls = set()
    
    try:
        with open(POSTED_SCORES_FILE, 'rb') as f:
            posted_scores = pickle.load(f)
    except FileNotFoundError:
        posted_scores = {}

def save_history():
    """Save the history of posted URLs and scores to disk."""
    with open(POSTED_URLS_FILE, 'wb') as f:
        pickle.dump(posted_urls, f)
    
    with open(POSTED_SCORES_FILE, 'wb') as f:
        pickle.dump(posted_scores, f)

def contains_goal_keyword(title):
    """Check if the post title contains any goal-related keywords or patterns."""
    for keyword in goal_keywords:
        if re.search(keyword, title.lower()):
            logging.debug(f"Goal keyword found: '{keyword}' in title: '{title}'")
            return True
    logging.debug(f"No goal keywords found in title: '{title}'")
    return False

def contains_specific_site(url):
    """Check if the URL contains any of the specific sites."""
    return any(site in url.lower() for site in specific_sites)

def contains_premier_league_team(title):
    """Check if the post title contains any Premier League team names or aliases."""
    title_lower = title.lower()
    for team, data in premier_league_teams.items():
        # Create patterns with word boundaries for each team name
        if any(re.search(r'\b' + re.escape(name.lower()) + r'\b', title_lower) for name in data["names"]):
            logging.debug(f"Premier League team found: '{team}' in title: '{title}'")
            return True
    logging.debug(f"No Premier League team found in title: '{title}'")
    return False

def get_direct_video_link(url):
    """Fetch the direct video link from the page."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    source_tag = soup.find('source')
    if source_tag and 'src' in source_tag.attrs:
        return source_tag['src']
    return None

def find_team_in_title(title):
    """Find the scoring team in the title based on square brackets and return its data"""
    # Look for the scoring pattern with square brackets
    score_pattern = re.search(r'(\d+)\s*-\s*\[\d+\]|\[\d+\]\s*-\s*(\d+)', title)
    if score_pattern:
        # Split title around the score
        parts = re.split(r'\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+', title)
        if len(parts) >= 2:
            # If score is [X] - Y, first team scored, else second team scored
            scoring_team_part = parts[0] if '[' in title.split('-')[0] else parts[1]
            
            # Find the matching team
            title_lower = scoring_team_part.lower()
            for team, data in premier_league_teams.items():
                if any(name.lower() in title_lower for name in data["names"]):
                    return data
    
    # Return None if we can't determine the scorer
    return None

def retry_mp4_extraction(title, urls):
    """Background task to retry MP4 extraction and post when found"""
    global mp4_retry_posts
    
    # Check if we're already processing this post
    if title in mp4_retry_posts:
        logging.debug(f"Already processing MP4 extraction for: {title}")
        return
        
    mp4_retry_posts.add(title)
    
    start_time = time.time()
    max_duration = 180  # 3 minutes in seconds
    attempt = 1
    
    while time.time() - start_time < max_duration:
        logging.info(f"MP4 extraction attempt {attempt} for: {title}")
        
        for url in urls:
            try:
                mp4_url = video_extractor.extract_mp4_url(url)
                if mp4_url:
                    logging.info(f"MP4 URL found on attempt {attempt}: {mp4_url}")
                    # Post just the MP4 to Discord
                    mp4_data = {
                        "content": mp4_url,
                        "username": DISCORD_USERNAME,
                        "avatar_url": DISCORD_AVATAR_URL
                    }
                    
                    response = requests.post(
                        DISCORD_WEBHOOK_URL,
                        json=mp4_data,
                        headers={'Content-Type': 'application/json'}
                    )
                    response.raise_for_status()
                    logging.info("Successfully posted MP4 URL to Discord")
                    mp4_retry_posts.remove(title)  # Remove from tracking set
                    return  # Exit the function once we've found and posted an MP4
            except Exception as e:
                logging.error(f"Error during MP4 retry: {e}")
        
        # Calculate remaining time
        elapsed = time.time() - start_time
        if elapsed < max_duration:
            # Sleep for 5 seconds between attempts, unless we're close to the max duration
            sleep_time = min(5, max_duration - elapsed)
            time.sleep(sleep_time)
            attempt += 1
    
    logging.warning(f"Failed to find MP4 URL after {attempt} attempts over 3 minutes for: {title}")
    failed_extractions_logger.info(f"Failed to find MP4 URL after {attempt} attempts over 3 minutes for: {title}")
    mp4_retry_posts.remove(title)  # Remove from tracking set after all attempts

def post_to_discord(title, url, mp4_url=None):
    """Post a formatted message to Discord using webhooks with rich embeds"""
    # Check if we're already processing this post
    if title in mp4_retry_posts:
        logging.debug(f"Skipping duplicate post: {title}")
        return
        
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    # Get team data
    team_data = find_team_in_title(title)
    
    # Create the embed
    embed = {
        "title": title,
        "color": team_data["color"] if team_data else 0x808080,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": []
    }
    
    # Add team thumbnail if found
    if team_data:
        embed["thumbnail"] = {"url": team_data["logo"]}
    
    # Add source link
    embed["fields"].append({
        "name": "Source",
        "value": f"[Original Link]({url})",
        "inline": True
    })

    try:
        # Send the styled embed immediately
        styled_data = {
            "embeds": [embed],
            "username": DISCORD_USERNAME,
            "avatar_url": DISCORD_AVATAR_URL
        }
        
        response = requests.post(
            webhook_url,
            json=styled_data,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        logging.info("Successfully posted styled message to Discord")
        
        # If we already have an MP4 URL, post it immediately
        if mp4_url:
            time.sleep(1)  # Small delay to ensure correct order
            mp4_data = {
                "content": mp4_url,
                "username": DISCORD_USERNAME,
                "avatar_url": DISCORD_AVATAR_URL
            }
            
            response = requests.post(
                webhook_url,
                json=mp4_data,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            logging.info("Successfully posted MP4 URL to Discord")
        else:
            # Start background retry process for MP4 extraction
            urls = [url]  # Add any additional URLs you want to try
            retry_thread = Thread(
                target=retry_mp4_extraction,
                args=(title, urls),
                daemon=True
            )
            retry_thread.start()
            
    except Exception as e:
        logging.error(f"Failed to post to Discord: {e}")

def cleanup_old_scores():
    """Remove scores older than 5 minutes from the posted_scores dictionary."""
    current_time = datetime.now(timezone.utc)
    expired_keys = [
        key for key, timestamp in posted_scores.items()
        if current_time - timestamp > timedelta(minutes=5)
    ]
    for key in expired_keys:
        del posted_scores[key]

def get_similarity_ratio(a, b):
    """Return a ratio of similarity between two strings."""
    return SequenceMatcher(None, a, b).ratio()

def normalize_score_pattern(title):
    """Extract and normalize just the score pattern (e.g., 'TeamA 0 - [1] TeamB')"""
    # First normalize the entire title
    normalized = title.lower().strip()
    
    # Remove variations in player names (e.g., "E. Haaland" vs "Erling Haaland" or "M. Lacroix" vs "Maxence Lacroix")
    # This handles both first name abbreviations and middle name abbreviations
    normalized = re.sub(r'(?:^|\s)([a-z]\.)\s*([a-z][a-zñ\']+(?:\s[a-z][a-zñ\']+)*)', 
                       lambda m: f' {m.group(2)}', 
                       normalized)
    
    # Extract teams and score including the scorer and minute
    score_match = re.search(r'(.+?\[\d+\].+?-[^-]+\d+\')', normalized)
    if score_match:
        # Normalize multiple spaces and trim
        return re.sub(r'\s+', ' ', score_match.group(1).strip())
    return normalized

def is_duplicate_score(title, timestamp):
    """Check if the same score for the same game is posted within 30 seconds."""
    normalized_score = normalize_score_pattern(title)
    logging.debug(f"\nChecking for duplicate:")
    logging.debug(f"Original title: {title}")
    logging.debug(f"Normalized score: {normalized_score}")
    
    # Extract score pattern and minute
    score_pattern = re.search(r'(\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+)', title)
    minute_pattern = re.search(r'(\d+)\'', title)
    
    if not score_pattern or not minute_pattern:
        return False
        
    current_score = score_pattern.group(1)
    current_minute = minute_pattern.group(1)
    
    # Check against recent posts
    for posted_title, posted_time in list(posted_scores.items()):
        time_diff = timestamp - posted_time.replace(tzinfo=timezone.utc)
        
        # Only check posts within last 300 seconds
        if time_diff.total_seconds() < 300:
            # Extract score and minute from posted title
            posted_score_match = re.search(r'(\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+)', posted_title)
            posted_minute_match = re.search(r'(\d+)\'', posted_title)
            
            if not posted_score_match or not posted_minute_match:
                continue
                
            posted_score = posted_score_match.group(1)
            posted_minute = posted_minute_match.group(1)
            
            # Calculate similarity for the full text
            similarity = get_similarity_ratio(title.lower(), posted_title.lower())
            
            logging.debug(f"Comparing with: {posted_title}")
            logging.debug(f"Score comparison - Current: {current_score}, Posted: {posted_score}")
            logging.debug(f"Minute comparison - Current: {current_minute}, Posted: {posted_minute}")
            logging.debug(f"Similarity ratio: {similarity}")
            
            # Consider it a duplicate only if:
            # 1. The score pattern is exactly the same
            # 2. The minute is exactly the same
            # 3. The overall similarity is very high
            if (current_score == posted_score and 
                current_minute == posted_minute and 
                similarity > 0.85):
                logging.debug("Duplicate found!")
                return True
    
    posted_scores[title] = timestamp
    cleanup_old_scores()
    return False

class VideoExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def validate_mp4_url(self, url):
        """Validate that an MP4 URL is complete and accessible"""
        if not url:
            return None
            
        # Ensure URL starts with https://
        if not url.startswith('https://'):
            logging.debug(f"Invalid URL format (no https://): {url}")
            return None
            
        try:
            # Try a HEAD request to validate the URL
            response = requests.head(url, headers=self.headers, timeout=5, allow_redirects=True)
            if response.status_code in [200, 302]:
                return url
            logging.debug(f"URL validation failed with status code {response.status_code}: {url}")
            return None
        except Exception as e:
            logging.error(f"Error validating URL {url}: {e}")
            return None

    def extract_from_streamff(self, url):
        """Extract MP4 URL from streamff.co"""
        try:
            video_id = url.split('/')[-1]
            mp4_url = f"https://ffedge.streamff.com/uploads/{video_id}.mp4"
            return self.validate_mp4_url(mp4_url)
        except Exception as e:
            logging.error(f"Error extracting from streamff: {e}")
            return None

    def extract_from_streamin(self, url):
        """Extract MP4 URL from streamin.one"""
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for source tags within video elements
            source = soup.find('source')
            if source and source.get('src'):
                # Remove the #t=0.1 fragment if present
                mp4_url = source['src']
                if '#t=' in mp4_url:
                    mp4_url = mp4_url.split('#')[0]
                return self.validate_mp4_url(mp4_url)
            # If no source tag, look for video tag
            video = soup.find('video')
            if video and video.get('src'):
                # Remove the #t=0.1 fragment if present
                mp4_url = video['src']
                if '#t=' in mp4_url:
                    mp4_url = mp4_url.split('#')[0]
                return self.validate_mp4_url(mp4_url)
            return None
        except Exception as e:
            logging.error(f"Error extracting from streamin: {e}")
            return None

    def extract_from_dubz(self, url):
        """Extract MP4 URL from dubz.link"""
        try:
            video_id = url.split('/')[-1]
            mp4_url = f"https://cdn.squeelab.com/guest/videos/{video_id}.mp4"
            return self.validate_mp4_url(mp4_url)
        except Exception as e:
            logging.error(f"Error extracting from dubz: {e}")
            return None

    def extract_mp4_url(self, url):
        """Main method to extract MP4 URL from supported sites"""
        logging.info(f"Attempting to extract MP4 from: {url}")
        
        try:
            if 'streamff.co' in url:
                return self.extract_from_streamff(url)
            elif any(domain in url for domain in streamin_domains):
                return self.extract_from_streamin(url)
            elif 'dubz.link' in url:
                return self.extract_from_dubz(url)
            else:
                logging.warning(f"Unsupported URL format: {url}")
                failed_extractions_logger.info(f"Unsupported URL format: {url}")
                return None
        except Exception as e:
            logging.error(f"Error extracting MP4 from {url}: {str(e)}")
            failed_extractions_logger.info(f"Error extracting MP4 from {url}: {str(e)}")
            return None

# Initialize the video extractor at the top level
video_extractor = VideoExtractor()

# Load history from disk
load_history()

def reprocess_history(hours_ago=24):
    """Reprocess posts from the last X hours without sending to Discord"""
    load_history()
    
    # Debug: Print the contents of pickle files
    print("\nDEBUG: Contents of pickle files")
    print(f"Posted URLs count: {len(posted_urls)}")
    print(f"Posted scores count: {len(posted_scores)}")
    
    # Calculate cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    
    print(f"\nTEST MODE: Reprocessing posts from the last {hours_ago} hours")
    print(f"Cutoff time: {cutoff_time}")
    print("-" * 80)
    
    # Create a new VideoExtractor
    video_extractor = VideoExtractor()
    
    # Keep track of processed items for summary
    processed_count = 0
    successful_extractions = 0
    
    # Process each URL in posted_urls
    for url in posted_urls:
        if contains_specific_site(url):
            processed_count += 1
            print(f"\nProcessing URL: {url}")
            
            mp4_url = video_extractor.extract_mp4_url(url)
            if mp4_url:
                successful_extractions += 1
                print(f"[+] Extracted MP4: {mp4_url}")
            else:
                print(f"[-] No MP4 URL found")
    
    # Print summary
    print("\n" + "=" * 80)
    print(f"TEST MODE SUMMARY:")
    print(f"Processed {processed_count} URLs")
    print(f"Successfully extracted {successful_extractions} MP4 URLs")
    print("=" * 80)

def debug_urls():
    """Debug mode: Process URLs from pickle files without posting to Discord"""
    load_history()
    
    print("\nDEBUG MODE: Processing URLs from pickle files")
    print(f"Found {len(posted_urls)} URLs to process")
    print("-" * 80)
    
    # Create a new VideoExtractor
    video_extractor = VideoExtractor()
    
    # Process each URL in posted_urls
    for url in posted_urls:
        if contains_specific_site(url):
            print(f"\nProcessing URL: {url}")
            
            # Try each video extractor method
            if "streamff.co" in url:
                print("Using streamff extractor")
                mp4_url = video_extractor.extract_from_streamff(url)
            elif any(domain in url for domain in streamin_domains):
                print("Using streamin extractor")
                mp4_url = video_extractor.extract_from_streamin(url)
            elif "dubz.link" in url:
                print("Using dubz extractor")
                mp4_url = video_extractor.extract_from_dubz(url)
            else:
                print("No matching extractor found")
                mp4_url = None
            
            if mp4_url:
                print(f"[+] Extracted MP4: {mp4_url}")
            else:
                print(f"[-] No MP4 URL found")
    
    print("\n" + "=" * 80)
    print(f"DEBUG MODE COMPLETE")
    print("=" * 80)

def check_rate_limit(response):
    """Check and log Reddit rate limit information from response headers."""
    remaining = response.headers.get('x-ratelimit-remaining')
    reset = response.headers.get('x-ratelimit-reset')
    used = response.headers.get('x-ratelimit-used')

    if remaining is not None and reset is not None and used is not None:
        logging.info(f"Rate Limit Info: {remaining} requests remaining, {used} used, resets in {reset} seconds.")
    else:
        logging.warning("Rate limit headers not found in response.")

def test_single_post():
    """Test mode: Send a single post to Discord from the first match found"""
    logging.info("Starting test mode - will send single post")
    
    try:
        # Fetch new posts from r/soccer
        subreddit = reddit.subreddit('soccer')
        
        # Iterate through the new posts of the subreddit
        for submission in subreddit.new(limit=25):  # Check more posts in test mode
            title = submission.title
            post_url = submission.url
            
            logging.debug(f"\nProcessing post: '{title}'")
            
            # Check if the post title contains a goal-related keyword and a Premier League team
            has_goal = contains_goal_keyword(title)
            has_team = contains_premier_league_team(title)
            
            if has_goal and has_team:
                logging.info(f"Found valid goal post: '{title}'")
                matched_urls = []
                
                # Check if the post URL contains the specific sites
                if contains_specific_site(post_url):
                    logging.debug(f"Found specific site URL in post: {post_url}")
                    matched_urls.append(post_url)
                
                # Check comments for URLs
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list():
                    comment_urls = re.findall(r'(https?://\S+)', comment.body)
                    for url in comment_urls:
                        if contains_specific_site(url):
                            logging.debug(f"Found specific site URL in comment: {url}")
                            matched_urls.append(url)
                
                # Process first matched URL and post to Discord
                if matched_urls:
                    url = matched_urls[0]
                    logging.info(f"Testing with URL: {url}")
                    
                    # Try to get direct MP4 URL
                    mp4_url = video_extractor.extract_mp4_url(url)
                    
                    if mp4_url:
                        logging.info(f"Using MP4 URL: {mp4_url}")
                        post_to_discord(title, url, mp4_url)
                    else:
                        logging.info(f"Using original URL: {url}")
                        post_to_discord(title, url)
                    
                    logging.info("Test post sent to Discord")
                    return  # Exit after sending one post
                
            else:
                logging.debug(f"Post skipped: has_goal={has_goal}, has_team={has_team}")
        
        logging.info("No matching posts found in test mode")
        
    except Exception as e:
        logging.error(f"Error in test mode: {e}")

# Initialize FastAPI app
app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Goal Bot with test modes')
    parser.add_argument('--test', type=int, help='Reprocess posts from the last X hours')
    parser.add_argument('--test-post', action='store_true', help='Send a single test post to Discord')
    parser.add_argument('--debug-urls', action='store_true', help='Debug mode: Process URLs without posting')
    args = parser.parse_args()

    # Start FastAPI in a separate thread
    api_thread = Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    if args.test:
        reprocess_history(args.test)
    elif args.test_post:
        test_single_post()
    elif args.debug_urls:
        debug_urls()
    else:
        # Normal bot operation
        while True:
            try:
                # Fetch new posts from r/soccer
                subreddit = reddit.subreddit('soccer')
                logging.info("Checking new posts in r/soccer...")
                
                # Iterate through the new posts of the subreddit
                for submission in subreddit.new(limit=10):
                    title = submission.title
                    post_url = submission.url
                    post_id = submission.id  # Get unique Reddit post ID
                    
                    # Skip if we've already processed this post
                    if post_id in posted_urls:
                        continue

                    logging.debug(f"\nProcessing post: '{title}'")
                    
                    # Check if the post title contains a goal-related keyword and a Premier League team
                    has_goal = contains_goal_keyword(title)
                    has_team = contains_premier_league_team(title)
                    
                    if has_goal and has_team:
                        logging.info(f"Found valid goal post: '{title}'")
                        matched_urls = []
                        
                        # Check if the post URL contains the specific sites
                        if contains_specific_site(post_url):
                            logging.debug(f"Found specific site URL in post: {post_url}")
                            matched_urls.append(post_url)
                        
                        # Check comments for URLs
                        submission.comments.replace_more(limit=0)
                        for comment in submission.comments.list():
                            comment_urls = re.findall(r'(https?://\S+)', comment.body)
                            for url in comment_urls:
                                if contains_specific_site(url):
                                    logging.debug(f"Found specific site URL in comment: {url}")
                                    matched_urls.append(url)
                        
                        if matched_urls:
                            # Try to get MP4 URL immediately first
                            mp4_url = video_extractor.extract_mp4_url(matched_urls[0])
                            # Post to Discord (will start retry process if no MP4 found)
                            post_to_discord(title, matched_urls[0], mp4_url)
                            
                            # Mark this post as processed
                            posted_urls.add(post_id)
                            save_history()  # Save to disk immediately
                    
                # Wait before next check
                time.sleep(15)
                
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(30)