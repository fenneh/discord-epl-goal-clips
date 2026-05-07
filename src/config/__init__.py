"""Configuration module for the goal bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read secrets from environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_AGENT = os.getenv("USER_AGENT")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_USERNAME = os.getenv("DISCORD_USERNAME", "Ally")  # Default to 'Ally' if not set
DISCORD_AVATAR_URL = os.getenv(
    "DISCORD_AVATAR_URL",
    "https://cdn1.rangersnews.uk/uploads/24/2024/03/GettyImages-459578698-scaled-e1709282146939-1024x702.jpg",
)  # Default to current image if not set

# Streams config (for daily schedule webhook)
STREAMS_URL = os.getenv("STREAMS_URL")
STREAMS_PASSWORD_FILE = "/app/streams/password.txt"

# Feature toggle for finding direct MP4 links (REMOVED - Currently unused)
# FIND_MP4_LINKS = True

# Post age cutoff in minutes (default 5 minutes)
POST_AGE_MINUTES = int(os.getenv("POST_AGE_MINUTES", "5"))

# Allowed domains for goal clips (REMOVED - Logic uses base_domains from filters.py)
# ALLOWED_DOMAINS = [
#     'streamff.com',
#     'streamin.me',
#     'dubz.co'
# ]

# Base directory for data storage
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# File paths for persistence
POSTED_URLS_FILE = DATA_DIR / "posted_urls.pkl"
POSTED_SCORES_FILE = DATA_DIR / "posted_scores.pkl"
