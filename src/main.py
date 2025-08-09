"""Main entry point for the goal bot application."""

import argparse
import asyncio
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Set, Dict, List, Optional

import asyncpraw
from fastapi import FastAPI, BackgroundTasks

from src.config import POSTED_URLS_FILE, POSTED_SCORES_FILE, POST_AGE_MINUTES
from src.config.domains import base_domains
from src.services.discord_service import post_to_discord, post_mp4_link
from src.services.reddit_service import (
    create_reddit_client,
    find_team_in_title,
    extract_mp4_link
)
from src.services.video_service import video_extractor
from src.utils.logger import app_logger
from src.utils.persistence import save_data, load_data
from src.utils.score_utils import (
    is_duplicate_score,
    cleanup_old_scores,
    extract_goal_info,
    generate_canonical_key
)
from src.utils.url_utils import get_domain_info

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
posted_scores: Dict[str, Dict[str, str]] = load_data(POSTED_SCORES_FILE, dict())

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
    excluded_patterns = [rf'\b{re.escape(term)}\b' for term in ['test']]
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
        reddit_url = f"https://reddit.com{submission.permalink}"
        
        app_logger.info("=" * 80)
        app_logger.info(f"New Submission: {title}")
        app_logger.info(f"Video URL:   {url}")
        app_logger.info(f"Reddit URL:  {reddit_url}")
        app_logger.info(f"Posted:      {post_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Skip old posts based on configured age limit
        if (current_time - post_time) > timedelta(minutes=POST_AGE_MINUTES):
            age_minutes = (current_time - post_time).total_seconds() / 60
            app_logger.info(f"[SKIP] Post too old: {age_minutes:.1f} min > {POST_AGE_MINUTES} min limit")
            return False
            
        # Check if title contains a Premier League team
        team_data = find_team_in_title(title, include_metadata=True)
        if not team_data:
            app_logger.info(f"[SKIP] No Premier League team found: {title}")
            return False
            
        # Skip if we've already processed this URL
        if url in posted_urls and not ignore_duplicates:
            app_logger.info(f"[SKIP] URL already processed: {url}")
            return False
            
        # Skip if title contains excluded terms
        if contains_excluded_term(title):
            app_logger.info(f"[SKIP] Contains excluded terms: {title}")
            return False
            
        # Check if this is a goal post
        if not contains_goal_keyword(title):
            app_logger.info(f"[SKIP] Not a goal post: {title}")
            return False
            
        # --- Updated Domain Check --- 
        domain_info = get_domain_info(url)
        if not domain_info:
            app_logger.warning(f"[SKIP] Could not parse domain for URL: {url}")
            return False
        
        full_domain = domain_info['full_domain']
        matched_base = domain_info['matched_base']
        app_logger.debug(f"Checking domain: {full_domain} (Matched base: {matched_base})")

        if not matched_base:
            app_logger.info(f"[SKIP] Domain not allowed: {full_domain}")
            return False
        # --- End Updated Domain Check ---
            
        # Extract goal info and generate canonical key first
        current_info = extract_goal_info(title)
        if not current_info:
            # If goal info can't be extracted, we can't reliably check for duplicates or store by key.
            # Option 1: Skip the post entirely
            # app_logger.warning(f"[SKIP] Could not extract goal info: {title}")
            # return False 
            # Option 2: Log warning and proceed without duplicate check/keyed storage (riskier)
            app_logger.warning(f"[PROCESS-WARN] Could not extract goal info for duplicate check/keying: {title}. Proceeding with caution.")
            canonical_key = None # Ensure key is None
        else:
            canonical_key = generate_canonical_key(current_info)
            if not canonical_key:
                app_logger.warning(f"[PROCESS-WARN] Could not generate canonical key for: {title}. Proceeding with caution.")
                # Still proceed, but won't be stored/checked by key
            elif not ignore_duplicates:
                 # Check if this is a duplicate score using the canonical key
                 if is_duplicate_score(title, posted_scores, current_time, url): # is_duplicate_score now uses the key internally
                     app_logger.info(f"[SKIP] Duplicate score detected based on canonical key.")
                     app_logger.info(f"Title:      {title}")
                     app_logger.info(f"Reddit URL: {reddit_url}")
                     return False
        # --- End Refactored Duplicate Check ---
            
        # Check if this is a duplicate score (OLD LOGIC - REMOVE/COMMENT OUT)
        # if not ignore_duplicates and is_duplicate_score(title, posted_scores, current_time, url):
        #     app_logger.info(f"[SKIP] Duplicate score detected")
        #     app_logger.info(f"Title:      {title}")
        #     app_logger.info(f"Reddit URL: {reddit_url}")
        #     return False
            
        app_logger.info("-" * 40)
        app_logger.info("[PROCESSING] Valid goal post")
        app_logger.info(f"Title:     {title}")
        app_logger.info(f"URL:       {url}")
        app_logger.info(f"Teams:     {team_data.get('name', 'Unknown Team Found')} (Scoring: {team_data.get('is_scoring', 'N/A')})") # Log matched team and scoring status
        app_logger.info("-" * 40)
        
        # Post initial content to Discord with both URLs in embed
        original_url = submission.url  # Get the original URL directly from submission
        content = f"{title}\n{original_url}\n{reddit_url}"  # Include both URLs
        app_logger.info(f"Posting initial content:\n{content}")
        await post_to_discord(content, team_data) # Pass the full team_data dict
        
        # Store score with Reddit post URL and video URL, using canonical key if available
        if canonical_key:
            posted_scores[canonical_key] = {
                'timestamp': current_time.isoformat(),
                'url': original_url,  # Store original URL
                'reddit_url': reddit_url,
                'original_title': title # Store original title for reference
            }
            app_logger.info(f"Stored score with key '{canonical_key}' - Original: {original_url}, Reddit: {reddit_url}")
        else:
            # Fallback: Store by original title if key couldn't be generated
            # Note: This won't prevent duplicates effectively if titles vary slightly.
             posted_scores[title] = {
                'timestamp': current_time.isoformat(),
                'url': original_url,
                'reddit_url': reddit_url,
                'original_title': title
            }
             app_logger.warning(f"Stored score using original title as key (no canonical key) - Original: {original_url}, Reddit: {reddit_url}")

        # Save posted_scores data (only need to save once)
        save_data(posted_scores, POSTED_SCORES_FILE)
        
        # Store score with Reddit post URL and video URL (OLD LOGIC - REMOVE/COMMENT OUT)
        # posted_scores[title] = {
        #     'timestamp': current_time.isoformat(),
        #     'url': original_url,  # Store original URL
        #     'reddit_url': reddit_url
        # }
        # app_logger.info(f"Stored URLs - Original: {original_url}, Reddit: {reddit_url}")
        
        # Try to extract MP4 link with retries
        mp4_url = await extract_mp4_with_retries(submission)
        app_logger.info(f"Extracted MP4 URL: {mp4_url}")
        
        if mp4_url and mp4_url != original_url:  # Only post MP4 if it's different from original URL
            app_logger.info(f"Posting MP4 URL (different from original)")
            # Send just the raw MP4 URL
            await post_mp4_link(title, mp4_url, team_data)
        else:
            app_logger.info(f"Skipping MP4 post - {'No MP4 URL found' if not mp4_url else 'Same as original URL'}")
            
        # Mark URL as processed (still useful for quick check of exact URLs)
        posted_urls.add(url)
        save_data(posted_urls, POSTED_URLS_FILE)
        # save_data(posted_scores, POSTED_SCORES_FILE) # No longer needed here, saved above
        
        return True
        
    except Exception as e:
        app_logger.error(f"Error processing submission: {e}")
        return False

async def check_new_posts(reddit_client: asyncpraw.Reddit, background_tasks: Optional[BackgroundTasks] = None) -> None:
    """Check for new goal posts on Reddit using an existing Reddit client."""
    try:
        app_logger.info("Checking new posts in r/soccer...")
        
        # Get subreddit
        try:
            subreddit = await reddit_client.subreddit('soccer')
            app_logger.info("Successfully got r/soccer subreddit")
        except Exception as e:
            app_logger.error(f"Failed to get subreddit: {str(e)}")
            return
        
        # Only get posts from configured time window
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=POST_AGE_MINUTES)
        app_logger.info(f"Looking for posts newer than {cutoff_time}")
        
        post_count = 0
        try:
            async for submission in subreddit.new(limit=200):
                # Skip posts older than configured age limit
                created_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                if created_time < cutoff_time:
                    app_logger.debug(f"Skipping old post from {created_time}: {submission.title}")
                    break  # Posts are in chronological order, so we can break
                
                post_count += 1
                if background_tasks:
                    background_tasks.add_task(process_submission, submission)
                else:
                    await process_submission(submission)
                    
            app_logger.info(f"Found {post_count} posts within the last {POST_AGE_MINUTES} minutes")
            
        except Exception as e:
            app_logger.error(f"Error iterating through posts: {str(e)}")
            return
            
    except Exception as e:
        app_logger.error(f"Top-level error in check_new_posts: {str(e)}")
        return

async def periodic_check():
    """Periodically check for new posts."""
    app_logger.info("Starting periodic check...")
    
    reddit_client = None  # Initialize client variable
    while True:
        try:
            # Create a new Reddit client if one doesn't exist or to refresh it periodically (e.g., after an error)
            if reddit_client is None:
                app_logger.info("Creating new Reddit client for periodic check.")
                reddit_client = await create_reddit_client()
            
            # Perform cleanup of old scores periodically
            if cleanup_old_scores(posted_scores):
                save_data(posted_scores, POSTED_SCORES_FILE) # Save if cleanup occurred
            
            await check_new_posts(reddit_client, None) # Pass the client
            
            # Sleep for 30 seconds between checks to avoid rate limits
            await asyncio.sleep(30)
            
        except asyncpraw.exceptions.RedditAPIException as e:
            app_logger.error(f"Reddit API Exception in periodic check: {str(e)}. Attempting to recreate client on next cycle.")
            if reddit_client:
                await reddit_client.close() # Close the potentially problematic client
            reddit_client = None # Signal to recreate client
            await asyncio.sleep(60) # Longer sleep on API errors
        except Exception as e:
            app_logger.error(f"Error in periodic check: {str(e)}", exc_info=True)
            if reddit_client:
                 await reddit_client.close() # Ensure client is closed on other errors too
            reddit_client = None # Signal to recreate client
            await asyncio.sleep(60)
        # No finally block needed here for reddit_client.close() as we want to reuse it,
        # and close it specifically on errors that might require a new client.

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
                await process_submission(submission, ignore_duplicates=True) # Ignore duplicates during testing?
                
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
    # For a manual trigger, it might be better to create a fresh client
    # or manage a global client more carefully if this endpoint is hit often.
    # For simplicity here, let's create one for the scope of this request.
    reddit_client = None
    try:
        reddit_client = await create_reddit_client()
        await check_new_posts(reddit_client, background_tasks)
    except Exception as e:
        app_logger.error(f"Error during manual check_posts: {e}", exc_info=True)
        return {"status": "Error occurred during check"}
    finally:
        if reddit_client:
            await reddit_client.close()
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
    sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)
    
    parser = argparse.ArgumentParser(description='Goal Bot')
    parser.add_argument('--test-hours', type=int, help='Test posts from the last N hours')
    parser.add_argument('--test-threads', nargs='+', help='Test specific Reddit thread IDs')
    args = parser.parse_args()
    
    if args.test_hours:
        asyncio.run(test_past_hours(args.test_hours))
    elif args.test_threads:
        asyncio.run(test_specific_threads(args.test_threads, ignore_posted=True))
    else:
        # Test specific post
        test_post_id = "1hj95zl"  # Aston Villa 1 0 Manchester City goal
        asyncio.run(test_specific_threads([test_post_id], ignore_posted=True))
        
        # Start the FastAPI app
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000)
