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

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env file
load_dotenv()

# Read secrets from environment variables
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

# Keywords to identify goal posts
goal_keywords = ["goal", "scores", "scored", r"\d{1,3}'", r"\[\d+\] - \d+"]  # Updated to handle up to 999 minutes

# Specific websites to match URLs
specific_sites = ["streamff.co", "streamin.one", "dubz.link"]

# Premier League teams and their aliases
premier_league_teams = [
    "Arsenal", "The Arsenal", "The Gunners",
    "Aston Villa", "Villa", 
    "Bournemouth", "AFC Bournemouth", "The Cherries",
    "Brentford", "The Bees",
    "Brighton", "Brighton & Hove Albion", "Brighton and Hove Albion", "The Seagulls",
    "Chelsea", "The Blues", 
    "Crystal Palace", "Palace", "The Eagles",
    "Everton", "The Toffees",
    "Fulham", "The Cottagers",
    "Ipswich Town", "Ipswich", "The Tractor Boys",
    "Leicester City", "Leicester", "The Foxes",
    "Liverpool", "The Reds",
    "Manchester City", "Man City",
    "Manchester United", "Man United", "Man Utd",
    "Newcastle United", "Newcastle", "The Magpies",
    "Nottingham Forest", "Forest",
    "Southampton", "Saints",
    "Tottenham", "Tottenham Hotspur", "Spurs",
    "West Ham", "West Ham United", "The Hammers",
    "Wolves", "Wolverhampton", "Wolverhampton Wanderers"
]

# Feature toggle for finding direct MP4 links
FIND_MP4_LINKS = False

# Set to keep track of posted URLs and scores
posted_urls = set()
posted_scores = {}

# File paths for persistence
POSTED_URLS_FILE = 'posted_urls.pkl'
POSTED_SCORES_FILE = 'posted_scores.pkl'

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
    return any(re.search(keyword, title.lower()) for keyword in goal_keywords)

def contains_specific_site(url):
    """Check if the URL contains any of the specific sites."""
    return any(site in url.lower() for site in specific_sites)

def contains_premier_league_team(title):
    """Check if the post title contains any Premier League team names or aliases."""
    return any(team.lower() in title.lower() for team in premier_league_teams)

def get_direct_video_link(url):
    """Fetch the direct video link from the page."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    source_tag = soup.find('source')
    if source_tag and 'src' in source_tag.attrs:
        return source_tag['src']
    return None

def post_to_discord(message):
    """Send a message to the Discord webhook."""
    data = {
        "content": message
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code != 204:
        print(f"Failed to send message to Discord: {response.status_code}, {response.text}")

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
    # Extract teams and score
    score_match = re.search(r'(.+?\d+\s*-\s*\[\d+\].+?(?=-))', title)
    if score_match:
        # Normalize spaces and convert to lowercase
        return re.sub(r'\s+', ' ', score_match.group(1).strip().lower())
    return title.lower()

def is_duplicate_score(title, timestamp):
    """Check if the same score for the same game is posted within 30 seconds."""
    normalized_score = normalize_score_pattern(title)
    logging.debug(f"\nChecking for duplicate:")
    logging.debug(f"Original title: {title}")
    logging.debug(f"Normalized score: {normalized_score}")
    
    # Check against recent posts
    for posted_title, posted_time in list(posted_scores.items()):
        time_diff = timestamp - posted_time.replace(tzinfo=timezone.utc)
        
        # Only check posts within last 300 seconds
        if time_diff.total_seconds() < 300:
            posted_normalized = normalize_score_pattern(posted_title)
            similarity = get_similarity_ratio(normalized_score, posted_normalized)
            logging.debug(f"Comparing with: {posted_title}")
            logging.debug(f"Normalized previous: {posted_normalized}")
            logging.debug(f"Similarity ratio: {similarity}")
            
            if similarity > 0.5:  # 50% similarity threshold
                logging.debug("Duplicate found!")
                return True
    
    posted_scores[title] = timestamp
    cleanup_old_scores()
    return False

# Load history from disk
load_history()

while True:
    try:
        # Fetch new posts from r/soccer
        subreddit = reddit.subreddit('soccer')

        # Iterate through the new posts of the subreddit
        for submission in subreddit.new(limit=10):  # Fetch the latest 10 posts
            title = submission.title
            post_url = submission.url
            timestamp = datetime.fromtimestamp(submission.created_utc, timezone.utc)

            # Check if the post title contains a goal-related keyword and a Premier League team
            if contains_goal_keyword(title) and contains_premier_league_team(title):
                matched_urls = []
                
                # Check if the post URL contains the specific sites
                if contains_specific_site(post_url):
                    matched_urls.append(post_url)
                
                # Check comments for URLs
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list():
                    comment_urls = re.findall(r'(https?://\S+)', comment.body)
                    for url in comment_urls:
                        if contains_specific_site(url):
                            matched_urls.append(url)
                
                # Print the matched URLs in the desired format and post to Discord
                if matched_urls and not is_duplicate_score(title, timestamp):
                    for url in matched_urls:
                        if url not in posted_urls:
                            if FIND_MP4_LINKS:
                                direct_video_link = get_direct_video_link(url)
                                if direct_video_link:
                                    message = f"{title}\n<{direct_video_link}>"
                                else:
                                    message = f"{title}\n<{url}>"
                            else:
                                message = f"{title}\n<{url}>"
                            print(f"[{timestamp}] {message}")  # Print with timestamp for local logging
                            post_to_discord(message)
                            posted_urls.add(url)
    
        # Save history to disk
        save_history()
        
        # Wait for a specified interval before checking for new posts again
        time.sleep(15)  # Wait for 15 seconds
    except Exception as e:
        print(f"Error occurred: {e}")
        time.sleep(30)  # Wait longer if there's an error