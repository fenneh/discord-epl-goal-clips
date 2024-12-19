"""Test duplicate detection with various title formats."""

import sys
from datetime import datetime, timezone, timedelta
from src.utils.score_utils import is_duplicate_score, extract_goal_info, normalize_player_name

def test_duplicate_detection():
    """Test duplicate detection with real examples."""
    print("\nTesting duplicate detection...")
    print("-" * 50)

    # Test cases
    test_cases = [
        # Test case 1: Gabriel Jesus variations
        {
            "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
            "title2": "Arsenal [3] - 1 Crystal Palace - G. Jesus 81'",
            "should_match": True
        },
        # Test case 2: Eddie Nketiah variations
        {
            "title1": "Arsenal 3 - [2] Crystal Palace - Eddie Nketiah 85'",
            "title2": "Arsenal 3 - [2] Crystal Palace - E. Nketiah 85'",
            "should_match": True
        }
    ]

    # Mock posted_scores data structure
    posted_scores = {}
    base_time = datetime.now(timezone.utc)

    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Title 1: {case['title1']}")
        print(f"Title 2: {case['title2']}")
        print(f"Should Match: {case['should_match']}")

        # Extract goal info for both titles
        info1 = extract_goal_info(case['title1'])
        info2 = extract_goal_info(case['title2'])
        
        print("\nExtracted Information:")
        print(f"Title 1 Info: {info1}")
        print(f"Title 2 Info: {info2}")

        # Test duplicate detection
        # First post title1
        posted_scores.clear()
        current_time = base_time
        posted_scores[case['title1']] = {
            'timestamp': current_time,
            'url': f'https://example.com/post{i}_1'
        }

        # Try to post title2 30 seconds later
        current_time = base_time + timedelta(seconds=30)
        is_duplicate = is_duplicate_score(
            case['title2'], 
            posted_scores, 
            current_time,
            url=f'https://example.com/post{i}_2'
        )

        print(f"\nResult: {'PASS' if is_duplicate == case['should_match'] else 'FAIL'}")
        print(f"Expected duplicate: {case['should_match']}")
        print(f"Got duplicate: {is_duplicate}")

        if is_duplicate != case['should_match']:
            print("Test failed!")
            return False

    print("\nAll tests passed!")
    return True

if __name__ == "__main__":
    # Configure console encoding for Windows
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    success = test_duplicate_detection()
    sys.exit(0 if success else 1)
