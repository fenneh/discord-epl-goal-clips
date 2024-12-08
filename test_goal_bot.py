import unittest
from datetime import datetime, timezone
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from goal_bot import normalize_score_pattern, is_duplicate_score, posted_scores

class TestGoalBot(unittest.TestCase):
    def setUp(self):
        # Clear posted_scores before each test
        posted_scores.clear()

    def test_normalize_score_pattern(self):
        test_cases = [
            # Test case 1: Abbreviated vs Full name (Haaland)
            (
                "Crystal Palace 1 - [1] Manchester City - E. Haaland 30'",
                "crystal palace 1 - [1] manchester city - haaland 30'"
            ),
            # Test case 2: Different name format (Lacroix)
            (
                "Crystal Palace [2] - 1 Manchester City - M. Lacroix 56'",
                "crystal palace [2] - 1 manchester city - lacroix 56'"
            ),
        ]

        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = normalize_score_pattern(input_title)
                self.assertEqual(result, expected)

    def test_duplicate_detection(self):
        test_cases = [
            # Test case 1: Haaland goal variations
            (
                "Crystal Palace 1 - [1] Manchester City - E. Haaland 30'",
                "Crystal Palace 1 - [1] Manchester City - Erling Haaland 30'",
                True  # Should be considered duplicate
            ),
            # Test case 2: Lacroix goal variations
            (
                "Crystal Palace [2] - 1 Manchester City - M. Lacroix 56'",
                "Crystal Palace [2] - 1 Manchester City - Maxence Lacroix 56'",
                True  # Should be considered duplicate
            ),
            # Test case 3: Different goals (should not be duplicate)
            (
                "Crystal Palace 1 - [1] Manchester City - E. Haaland 30'",
                "Crystal Palace [2] - 1 Manchester City - M. Lacroix 56'",
                False
            ),
            # Test case 4: Same minute, different score (should not be duplicate)
            (
                "Crystal Palace 1 - [1] Manchester City - E. Haaland 30'",
                "Crystal Palace 1 - [2] Manchester City - E. Haaland 30'",
                False
            ),
        ]

        for title1, title2, should_be_duplicate in test_cases:
            with self.subTest(title1=title1, title2=title2):
                # Clear posted_scores before each subtest
                posted_scores.clear()
                
                # Use a fixed timestamp for testing
                timestamp = datetime.now(timezone.utc)
                
                # Post the first title
                is_duplicate_score(title1, timestamp)
                
                # Check if second title is considered duplicate
                result = is_duplicate_score(title2, timestamp)
                self.assertEqual(
                    result, 
                    should_be_duplicate, 
                    f"Expected duplicate={should_be_duplicate} for:\n{title1}\n{title2}"
                )

if __name__ == '__main__':
    unittest.main()
