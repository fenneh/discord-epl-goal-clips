"""Comprehensive duplicate detection tests with many team name variations."""

import pytest
from datetime import datetime, timezone
from src.utils.score_utils import is_duplicate_score, normalize_team_name

# Test cases with many variations of team names and scores
test_cases = [
    # Arsenal variations
    {
        "title1": "Arsenal 2 - [3] Manchester City - Haaland 45'",
        "title2": "The Gunners 2 - [3] Man City - E. Haaland 45'",
        "should_match": True,
        "reason": "Arsenal nickname variation"
    },
    {
        "title1": "Arsenal FC [1] - 0 Manchester United - Saka 23'",
        "title2": "Arsenal Football Club [1] - 0 Man Utd - Bukayo Saka 23'",
        "should_match": True,
        "reason": "FC/Football Club variation"
    },
    
    # Manchester variations
    {
        "title1": "Man United 0 - [2] Man City - Foden 67'",
        "title2": "Manchester United 0 - [2] Manchester City - P. Foden 67'",
        "should_match": True,
        "reason": "Man/Manchester variation"
    },
    {
        "title1": "MUFC 1 - [3] MCFC - De Bruyne 55'",
        "title2": "Manchester United 1 - [3] Manchester City - K. De Bruyne 55'",
        "should_match": True,
        "reason": "Abbreviation variation"
    },
    
    # Wolves variations
    {
        "title1": "Wolves [2] - 1 Leicester - Neto 78'",
        "title2": "Wolverhampton Wanderers [2] - 1 Leicester City - Pedro Neto 78'",
        "should_match": True,
        "reason": "Full name vs short name"
    },
    {
        "title1": "WWFC [4] - 2 Brighton - Cunha 89'",
        "title2": "Wolves [4] - 2 Brighton & Hove Albion - Matheus Cunha 89'",
        "should_match": True,
        "reason": "Abbreviation and full name variation"
    },
    
    # Brighton variations
    {
        "title1": "Brighton 3 - [4] Newcastle - Wilson 90+2'",
        "title2": "Brighton & Hove Albion 3 - [4] Newcastle United - C. Wilson 90+2'",
        "should_match": True,
        "reason": "Full name with ampersand"
    },
    {
        "title1": "Brighton and Hove [2] - 0 Palace - March 15'",
        "title2": "Brighton & Hove Albion [2] - 0 Crystal Palace - Solly March 15'",
        "should_match": True,
        "reason": "'and' vs '&' variation"
    },
    
    # Palace variations
    {
        "title1": "Crystal Palace [1] - 0 West Ham - Eze 34'",
        "title2": "Palace [1] - 0 West Ham United - E. Eze 34'",
        "should_match": True,
        "reason": "Short vs full name"
    },
    
    # Spurs variations
    {
        "title1": "Tottenham 2 - [3] Liverpool - Salah 71'",
        "title2": "Spurs 2 - [3] Liverpool FC - M. Salah 71'",
        "should_match": True,
        "reason": "Nickname variation"
    },
    {
        "title1": "THFC [2] - 1 Chelsea - Son 44'",
        "title2": "Tottenham Hotspur [2] - 1 Chelsea FC - Son Heung-min 44'",
        "should_match": True,
        "reason": "Abbreviation vs full name"
    },
    
    # Time variations
    {
        "title1": "Newcastle 1 - [2] Aston Villa - Watkins 89'",
        "title2": "Newcastle United 1 - [2] Villa - Ollie Watkins 90'",
        "should_match": True,
        "reason": "1 minute time difference"
    },
    {
        "title1": "Everton [3] - 1 Burnley - Calvert-Lewin 45+1'",
        "title2": "Everton [3] - 1 Burnley - DCL 45+2'",
        "should_match": True,
        "reason": "Injury time variation"
    },
    
    # Should NOT match
    {
        "title1": "Man City [2] - 0 Chelsea - Haaland 45'",
        "title2": "Man City [2] - 0 Chelsea - Foden 67'",
        "should_match": False,
        "reason": "Different minute, different scorer"
    },
    {
        "title1": "Liverpool 1 - [1] Arsenal - Saka 30'",
        "title2": "Liverpool 1 - [2] Arsenal - Martinelli 45'",
        "should_match": False,
        "reason": "Different score state"
    },
    {
        "title1": "Wolves [1] - 0 Brentford - Neto 15'",
        "title2": "Wolves [2] - 0 Brentford - Neto 45'",
        "should_match": False,
        "reason": "Different score, different minute"
    }
]

def test_comprehensive_duplicates():
    """Test duplicate detection with many variations."""
    print("\nTesting comprehensive duplicate detection...")
    print("-" * 80)
    
    for case in test_cases:
        print(f"\nTest case: {case['reason']}")
        print(f"Title 1: {case['title1']}")
        print(f"Title 2: {case['title2']}")
        print(f"Should match: {case['should_match']}")
        
        # Create a posted_scores dict with the first title
        posted_scores = {
            case['title1']: {
                'timestamp': datetime.now(timezone.utc),
                'url': 'https://example.com/1',
                'reddit_url': 'https://reddit.com/1'
            }
        }
        
        # Check if second title is considered a duplicate
        is_duplicate = is_duplicate_score(
            case['title2'],
            posted_scores,
            datetime.now(timezone.utc),
            'https://example.com/2'
        )
        
        assert is_duplicate == case['should_match'], (
            f"Expected match={case['should_match']}, got {is_duplicate}\n"
            f"Title 1: {case['title1']}\n"
            f"Title 2: {case['title2']}\n"
            f"Reason: {case['reason']}"
        )
        
        print(f"Result: {'PASS' if is_duplicate == case['should_match'] else 'FAIL'}")
        
        # Also test in reverse order
        posted_scores = {
            case['title2']: {
                'timestamp': datetime.now(timezone.utc),
                'url': 'https://example.com/2',
                'reddit_url': 'https://reddit.com/2'
            }
        }
        
        is_duplicate = is_duplicate_score(
            case['title1'],
            posted_scores,
            datetime.now(timezone.utc),
            'https://example.com/1'
        )
        
        assert is_duplicate == case['should_match'], (
            f"Expected match={case['should_match']}, got {is_duplicate}\n"
            f"Title 1: {case['title2']}\n"
            f"Title 2: {case['title1']}\n"
            f"Reason: {case['reason']} (reverse order)"
        )
        
        print(f"Result (reverse): {'PASS' if is_duplicate == case['should_match'] else 'FAIL'}")

def test_team_name_variations():
    """Test that team name normalization handles all variations."""
    variations = [
        # Arsenal
        ("Arsenal", "arsenal"),
        ("The Arsenal", "arsenal"),
        ("Arsenal FC", "arsenal"),
        ("The Gunners", "arsenal"),
        
        # Manchester teams
        ("Manchester United", "manchester"),
        ("Man United", "manchester"),
        ("Man Utd", "manchester"),
        ("MUFC", "manchester"),
        ("Manchester City", "manchester"),
        ("Man City", "manchester"),
        ("MCFC", "manchester"),
        
        # Wolves
        ("Wolves", "wolves"),
        ("Wolverhampton", "wolves"),
        ("Wolverhampton Wanderers", "wolves"),
        ("WWFC", "wolves"),
        
        # Brighton
        ("Brighton", "brighton"),
        ("Brighton & Hove", "brighton"),
        ("Brighton and Hove", "brighton"),
        ("Brighton & Hove Albion", "brighton"),
        
        # Palace
        ("Crystal Palace", "crystal"),
        ("Palace", "crystal"),
        ("CPFC", "crystal"),
        
        # Spurs
        ("Tottenham", "tottenham"),
        ("Spurs", "tottenham"),
        ("Tottenham Hotspur", "tottenham"),
        ("THFC", "tottenham"),
        
        # Leicester
        ("Leicester", "leicester"),
        ("Leicester City", "leicester"),
        ("LCFC", "leicester"),
        
        # Newcastle
        ("Newcastle", "newcastle"),
        ("Newcastle United", "newcastle"),
        ("Newcastle Utd", "newcastle"),
        ("NUFC", "newcastle"),
    ]
    
    print("\nTesting team name normalizations...")
    print("-" * 80)
    
    for original, expected in variations:
        normalized = normalize_team_name(original)
        print(f"{original:25} -> {normalized:15}")
        assert normalized == expected, f"Expected '{expected}', got '{normalized}' for '{original}'"

if __name__ == "__main__":
    test_comprehensive_duplicates()
    test_team_name_variations()
