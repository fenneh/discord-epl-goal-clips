"""Configuration module for the goal bot."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read secrets from environment variables
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
DISCORD_USERNAME = os.getenv('DISCORD_USERNAME', 'Ally')  # Default to 'Ally' if not set
DISCORD_AVATAR_URL = os.getenv('DISCORD_AVATAR_URL', 'https://cdn1.rangersnews.uk/uploads/24/2024/03/GettyImages-459578698-scaled-e1709282146939-1024x702.jpg')  # Default to current image if not set

# Feature toggle for finding direct MP4 links
FIND_MP4_LINKS = True

# Allowed domains for goal clips
ALLOWED_DOMAINS = [
    'streamff.com',
    'streamin.me',
    'dubz.co'
]

# Base directory for data storage
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# File paths for persistence
POSTED_URLS_FILE = os.path.join(DATA_DIR, 'posted_urls.pkl')
POSTED_SCORES_FILE = os.path.join(DATA_DIR, 'posted_scores.pkl')
