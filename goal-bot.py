import os
import praw
import re
import requests
import time
import pickle
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from dotenv import load_dotenv

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
goal_keywords = ["goal", "scores", "scored", r"\d{1,2}'", r"\[\d+\] - \d+"]  # Expanded to include minute and score patterns

# Specific websites to match URLs
specific_sites = ["streamff.co", "streamin.one", "dubz.link"]

# Premier League teams and their aliases
premier_league_teams = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Burnley", 
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton Town", 
    "Manchester City", "Man City", "Manchester United", "Man Utd", "Newcastle United", 
    "Nottingham Forest", "Sheffield United", "Tottenham Hotspur", "Spurs", 
    "West Ham United", "Wolves", "Wolverhampton Wanderers"
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

def is_duplicate_score(title, timestamp):
    """Check if the same score for the same game is posted within 30 seconds."""
    score_pattern = re.search(r'\[\d+\] - \d+', title)
    if score_pattern:
        score = score_pattern.group()
        key = f"{title.split('-')[0].strip()} {score}"
        if key in posted_scores:
            last_posted_time = posted_scores[key].replace(tzinfo=timezone.utc)
            if timestamp - last_posted_time < timedelta(seconds=30):
                return True
        posted_scores[key] = timestamp
    return False

# Load history from disk
load_history()

while True:
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