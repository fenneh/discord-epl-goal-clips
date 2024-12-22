"""Test duplicate detection with various title formats."""

import sys
from datetime import datetime, timezone, timedelta
from src.utils.score_utils import is_duplicate_score, extract_goal_info, normalize_player_name
from src.services.reddit_service import find_team_in_title

def test_duplicate_detection():
    """Test duplicate detection with real examples."""
    print("\nTesting duplicate detection...")
    print("-" * 50)

    # Test cases
    test_cases = [
        # Real example from Villa vs City game
        {
            "title1": "Aston Villa [2] - 0 Manchester City - M. Rogers 65'",
            "title2": "Aston Villa [2] - 0 Manchester City - Morgan Rogers 65'",
            "url1": "https://streamin.one/v/njrvnxx0",
            "url2": "https://streamff.live/v/1021e06e",
            "should_match": True,
            "time_diff": 30  # 30 seconds
        },
        # Case 1: Arsenal's 5th goal
        {
            "title1": "Crystal Palace 1 - [5] Arsenal - D. Rice 84'",
            "title2": "Crystal Palace 1 - [5] Arsenal - Declan Rice 84'",
            "url1": "https://streamin.one/v/9740dc7b",
            "url2": "https://streamff.live/v/7a227279",
            "should_match": True,
            "time_diff": 30
        },
        # Case 2: Arsenal's 4th goal
        {
            "title1": "Crystal Palace 1 - [4] Arsenal - Gabriel Martinelli 60'",
            "title2": "Crystal Palace 1 - [4] Arsenal - Gabriel Martinelli 60'",
            "url1": "https://streamin.one/v/c054a039",
            "url2": "https://streamff.live/v/c7b7ac12",
            "should_match": True,
            "time_diff": 30
        },
        # Case 3: Different goals (control case)
        {
            "title1": "Crystal Palace 1 - [4] Arsenal - Gabriel Martinelli 60'",
            "title2": "Crystal Palace 1 - [5] Arsenal - D. Rice 84'",
            "url1": "https://streamin.one/v/c054a039",
            "url2": "https://streamin.one/v/9740dc7b",
            "should_match": False,
            "time_diff": 30
        },
        {
            "title1": "Manchester Utd 0 - [1] Bournemouth - Dean Huijsen 29'",
            "title2": "Manchester United 0 - [1] Bournemouth - Dean Huijsen 29'",
            "url1": "https://streamin.one/v/njrvnxx0",
            "url2": "https://streamff.live/v/1021e06e",
            "should_match": True,
            "time_diff": 30  # 30 seconds
        },
        {
            "title1": "Leicester 0 - [2] Wolves - Rodrigo Gomes 36'",
            "title2": "Leicester City 0 - [2] Wolves - Rodrigo Gomes 36'",
            "url1": "https://streamin.one/v/njrvnxx0",
            "url2": "https://streamff.live/v/1021e06e",
            "should_match": True,
            "time_diff": 30  # 30 seconds
        }
    ]

    # Mock posted_scores data structure
    posted_scores = {}
    base_time = datetime.now(timezone.utc)

    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Title 1: {case['title1']}")
        print(f"Title 2: {case['title2']}")
        print(f"URL 1: {case['url1']}")
        print(f"URL 2: {case['url2']}")
        print(f"Should Match: {case['should_match']}")
        print(f"Time Difference: {case.get('time_diff', 30)} seconds")

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
            'timestamp': current_time.isoformat(),
            'url': case['url1']
        }

        # Try to post title2 after specified time difference
        current_time = base_time + timedelta(seconds=case.get('time_diff', 30))
        is_duplicate = is_duplicate_score(
            case['title2'], 
            posted_scores, 
            current_time,
            url=case['url2']
        )

        print(f"\nResult: {'PASS' if is_duplicate == case['should_match'] else 'FAIL'}")
        print(f"Expected duplicate: {case['should_match']}")
        print(f"Got duplicate: {is_duplicate}")

        if is_duplicate != case['should_match']:
            print("Test failed!")
            return False

    print("\nAll tests passed!")
    return True

def test_team_logo_detection():
    """Test that we get the correct team logo for goals."""
    # Test cases
    test_cases = [
        {
            "title": "Leicester City 0 - [1] Wolves - Goncalo Guedes 19'",
            "expected_team": "Wolves",
            "expected_logo": "https://resources.premierleague.com/premierleague/badges/t39.png",
            "expected_is_scoring": True
        }
    ]
    
    print("\nTesting team logo detection...")
    print("-" * 50)
    
    for case in test_cases:
        print(f"\nTest case:")
        print(f"Title: {case['title']}")
        print(f"Expected team: {case['expected_team']}")
        
        # Get team data with metadata
        result = find_team_in_title(case['title'], include_metadata=True)
        
        assert result is not None, "Failed to find any team"
        assert result['name'] == case['expected_team'], f"Expected {case['expected_team']}, got {result['name']}"
        assert result['data']['logo'] == case['expected_logo'], f"Wrong logo URL"
        assert result['is_scoring'] == case['expected_is_scoring'], f"Wrong scoring flag"
        
        print(f"Result: PASS")
        print(f"Found team: {result['name']}")
        print(f"Logo URL: {result['data']['logo']}")
        print(f"Is scoring: {result['is_scoring']}")

if __name__ == "__main__":
    # Configure console encoding for Windows
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    success = test_duplicate_detection()
    test_team_logo_detection()
    sys.exit(0 if success else 1)
