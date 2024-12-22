from datetime import datetime, timezone
from src.utils.score_utils import extract_goal_info, is_duplicate_score

def test_duplicate_detection():
    # Test titles
    title1 = "Crystal Palace 1 - [3] Arsenal - K. Havertz 38'"
    title2 = "Crystal Palace 1 - [3] Arsenal - Kai Havertz 38'"
    
    # Create test timestamp
    timestamp = datetime.now(timezone.utc)
    
    # Create posted_scores with first title
    posted_scores = {
        title1: {
            'timestamp': timestamp.isoformat(),
            'url': 'https://streamin.one/v/p9ckss03',
            'reddit_url': 'test_reddit_1'
        }
    }
    
    # Print extracted info for both titles
    print("\nTitle 1 Info:")
    info1 = extract_goal_info(title1)
    print(info1)
    
    print("\nTitle 2 Info:")
    info2 = extract_goal_info(title2)
    print(info2)
    
    # Test if second title is detected as duplicate
    print("\nChecking for duplicate...")
    is_duplicate = is_duplicate_score(title2, posted_scores, timestamp, 'test_url_2')
    print(f"Is duplicate: {is_duplicate}")

if __name__ == "__main__":
    test_duplicate_detection()
