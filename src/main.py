"""Main entry point for the goal bot application."""

import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from typing import Set, Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from src.services.reddit_service import create_reddit_client, find_team_in_title, extract_mp4_link
from src.services.discord_service import post_to_discord, post_mp4_link
from src.services.video_service import video_extractor
from src.utils.persistence import save_data, load_data
from src.utils.url_utils import is_valid_domain, get_base_domain
from src.utils.logger import app_logger
from src.utils.score_utils import is_duplicate_score, cleanup_old_scores
from src.config import POSTED_URLS_FILE, POSTED_SCORES_FILE, FIND_MP4_LINKS, ALLOWED_DOMAINS
from src.utils.keywords import GOAL_KEYWORDS, EXCLUDED_TERMS
import re

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events."""
    # Startup
    app_logger.info("Goal bot starting up...")
    # Start periodic check task
    task = asyncio.create_task(periodic_check())
    yield
    # Shutdown
    app_logger.info("Shutting down...")
    # Cancel periodic check task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# Load previously posted URLs and scores
posted_urls: Set[str] = load_data(POSTED_URLS_FILE, set())
posted_scores: Dict[str, Dict[str, str]] = load_data(POSTED_SCORES_FILE, {})

def contains_goal_keyword(title: str) -> bool:
    """Check if the post title contains any goal-related keywords or patterns.
    
    Args:
        title (str): Post title to check
        
    Returns:
        bool: True if title contains goal keywords, False otherwise
    """
    title_lower = title.lower()
    
    # Check for score patterns first
    score_patterns = [
        r'\[\d+\]',  # [1]
        r'\d+\s*-\s*\[\d+\]',  # 0 - [1]
        r'\[\d+\]\s*-\s*\d+',  # [1] - 0
        r'\[\d+\s*-\s*\d+\]',  # [1-0]
    ]
    
    for pattern in score_patterns:
        if re.search(pattern, title):
            return True
            
    # Check for goal keywords and emojis
    goal_indicators = {
        'goal', 'score', 'scores', 'scored', 'scoring',
        'strike', 'finish', 'tap in', 'header', 'penalty',
        'free kick', 'volley', '⚽'  # Added soccer ball emoji
    }
    
    return any(indicator in title_lower for indicator in goal_indicators)

def contains_excluded_term(title: str) -> bool:
    """Check if the post title contains any excluded terms.
    
    Args:
        title (str): Post title to check
        
    Returns:
        bool: True if title contains excluded terms, False otherwise
    """
    title_lower = title.lower()
    
    # Add word boundaries to prevent partial matches
    excluded_patterns = [rf'\b{re.escape(term)}\b' for term in EXCLUDED_TERMS]
    return any(re.search(pattern, title_lower) for pattern in excluded_patterns)

async def extract_mp4_with_retries(submission, max_retries: int = 30, delay: int = 10) -> Optional[str]:
    """Try to extract MP4 link with retries.
    
    Args:
        submission: Reddit submission
        max_retries: Maximum number of retries (default 30 = 5 minutes with 10s delay)
        delay: Delay between retries in seconds
        
    Returns:
        str: MP4 link if found, None otherwise
    """
    for attempt in range(max_retries):
        try:
            mp4_link = await extract_mp4_link(submission)
            if mp4_link:
                app_logger.info(f"Successfully extracted MP4 link on attempt {attempt + 1}: {mp4_link}")
                return mp4_link
            
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                app_logger.info(f"MP4 link not found, retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                
        except Exception as e:
            app_logger.error(f"Error extracting MP4 link on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                
    app_logger.warning("Failed to extract MP4 link after all retries")
    return None

async def process_submission(submission, ignore_duplicates: bool = False) -> bool:
    """Process a Reddit submission for goal clips.
    
    Args:
        submission: Reddit submission object
        ignore_duplicates: If True, ignore duplicate scores
        
    Returns:
        bool: True if post should be processed, False otherwise
    """
    try:
        title = submission.title
        url = submission.url
        current_time = datetime.now(timezone.utc)
        post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        
        # Skip old posts (more than 5 minutes old)
        if (current_time - post_time) > timedelta(minutes=5):
            app_logger.debug(f"Skipping old post: {title}")
            return False
            
        # Skip if we've already processed this URL
        if url in posted_urls and not ignore_duplicates:
            app_logger.debug(f"Skipping already posted URL: {url}")
            return False
            
        # Skip if title contains excluded terms
        if contains_excluded_term(title):
            app_logger.debug(f"Title contains excluded terms: {title}")
            return False
            
        # Check if this is a goal post
        if not contains_goal_keyword(title):
            app_logger.debug(f"Not a goal post: {title}")
            return False
            
        # Check if URL domain is allowed
        base_domain = get_base_domain(url)
        if base_domain not in ALLOWED_DOMAINS:
            app_logger.debug(f"URL domain not allowed: {base_domain}")
            return False
            
        # Check if title contains a Premier League team
        team_data = find_team_in_title(title, include_metadata=True)
        if not team_data:
            app_logger.debug(f"No Premier League team found in title: {title}")
            return False
            
        # Post initial content to Discord
        content = f"**{title}**\n{url}"
        await post_to_discord(content, team_data)
        
        # Try to extract MP4 link with retries
        mp4_url = await extract_mp4_with_retries(submission)
        if mp4_url:
            # Send a follow-up with just the MP4 link
            await post_mp4_link(title, mp4_url, team_data)
            
        # Mark URL as processed
        posted_urls.add(url)
        save_data(posted_urls, POSTED_URLS_FILE)
        
        return True
        
    except Exception as e:
        app_logger.error(f"Error processing submission: {e}")
        return False

async def check_new_posts(background_tasks: BackgroundTasks) -> None:
    """Check for new goal posts on Reddit."""
    try:
        reddit = await create_reddit_client()
        subreddit = await reddit.subreddit('soccer')
        
        # Only get posts from last 5 minutes
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        async for submission in subreddit.new(limit=200):
            # Skip posts older than 5 minutes
            created_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
            if created_time < cutoff_time:
                app_logger.debug(f"Skipping old post from {created_time}: {submission.title}")
                break  # Posts are in chronological order, so we can break
                
            if background_tasks:
                background_tasks.add_task(process_submission, submission)
            else:
                await process_submission(submission)
                
    except Exception as e:
        app_logger.error(f"Error checking new posts: {str(e)}")
    finally:
        await reddit.close()

async def periodic_check():
    """Periodically check for new posts."""
    while True:
        try:
            app_logger.info("Checking new posts in r/soccer...")
            await check_new_posts(None)  # Pass None since we're not using background tasks here
            cleanup_old_scores(posted_scores)  # Cleanup old scores
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            app_logger.error(f"Error in periodic check: {str(e)}")
            await asyncio.sleep(30)  # Still wait before retrying

async def test_past_hours(hours: int = 2) -> None:
    """Test the bot by processing posts from the past X hours.
    
    Args:
        hours (int): Number of hours to look back
    """
    try:
        app_logger.info(f"Testing posts from the past {hours} hours...")
        
        reddit = await create_reddit_client()
        subreddit = await reddit.subreddit('soccer')
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        processed = 0
        found = 0
        
        async for submission in subreddit.new(limit=500):  # Increase limit to find older posts
            created_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
            if created_time < cutoff_time:
                break
                
            processed += 1
            title = submission.title
            if ('goal' in title.lower() or 'score' in title.lower()):
                found += 1
                app_logger.info(f"Found goal post: {title}")
                await process_submission(submission)
                
        app_logger.info(f"Test complete. Processed {processed} posts, found {found} goal posts.")
        
    except Exception as e:
        app_logger.error(f"Error in test: {str(e)}")
    finally:
        await reddit.close()  # Close the Reddit client session

async def test_specific_threads(thread_ids: List[str], ignore_posted: bool = False, ignore_duplicates: bool = False) -> None:
    """Test processing specific Reddit threads.
    
    Args:
        thread_ids (List[str]): List of Reddit thread IDs to test
        ignore_posted (bool): If True, ignore whether thread has been posted before
        ignore_duplicates (bool): If True, ignore duplicate scores
    """
    app_logger.info(f"Testing {len(thread_ids)} specific threads...")
    reddit = await create_reddit_client()
    
    for thread_id in thread_ids:
        try:
            submission = await reddit.submission(thread_id)
            title = submission.title
            app_logger.info(f"\nProcessing thread: {title}")
            app_logger.info(f"URL: {submission.url}")
            
            if ignore_posted:
                # Temporarily remove URL from posted_urls if it exists
                was_posted = submission.url in posted_urls
                if was_posted:
                    posted_urls.remove(submission.url)
                    
            await process_submission(submission, ignore_duplicates)
            
            if ignore_posted and was_posted:
                # Restore URL to posted_urls if it was there before
                posted_urls.add(submission.url)
                
        except Exception as e:
            app_logger.error(f"Error processing thread {thread_id}: {str(e)}")
            
    await reddit.close()  # Close the Reddit client session
    app_logger.info("Test complete. Processed {} threads.".format(len(thread_ids)))

def clean_text(text: str) -> str:
    """Clean text to handle unicode characters."""
    return text.encode('ascii', 'ignore').decode('utf-8')

@app.get("/check")
async def check_posts(background_tasks: BackgroundTasks):
    """Endpoint to manually trigger post checking.
    
    Args:
        background_tasks: FastAPI background tasks
        
    Returns:
        dict: Status message
    """
    await check_new_posts(background_tasks)
    return {"status": "Checking for new posts"}

@app.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        dict: Status message
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    # Configure console encoding for Windows
    import sys
    import codecs
    if sys.platform == 'win32':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    parser = argparse.ArgumentParser(description="Run the goal bot")
    parser.add_argument(
        "--test-threads",
        nargs="+",
        help="Test specific Reddit thread IDs"
    )
    parser.add_argument(
        "--ignore-posted",
        action="store_true",
        help="Ignore whether threads have been posted before"
    )
    parser.add_argument(
        "--ignore-duplicates",
        action="store_true",
        help="Ignore duplicate scores when testing"
    )
    args = parser.parse_args()
    
    if args.test_threads:
        asyncio.run(test_specific_threads(args.test_threads, args.ignore_posted, args.ignore_duplicates))
    else:
        import uvicorn
        uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
