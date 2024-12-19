"""Test suite for score utilities."""

import unittest
from datetime import datetime, timezone, timedelta
from src.utils.score_utils import (
    is_duplicate_score,
    extract_goal_info,
    normalize_player_name,
    normalize_score_pattern
)

class TestScoreUtils(unittest.TestCase):
    """Test cases for score utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_time = datetime.now(timezone.utc)
        self.posted_scores = {}

    def test_normalize_player_name(self):
        """Test player name normalization."""
        test_cases = [
            # Full name vs abbreviated
            ("Gabriel Jesus", "jesus"),
            ("G. Jesus", "jesus"),
            ("Eddie Nketiah", "nketiah"),
            ("E. Nketiah", "nketiah"),
            # Accented characters
            ("João Félix", "felix"),
            ("J. Félix", "felix"),
            # Multiple word last names
            ("Virgil van Dijk", "van dijk"),
            ("V. van Dijk", "van dijk"),
            # Hyphenated names
            ("Smith-Rowe", "smith-rowe"),
            ("E. Smith-Rowe", "smith-rowe"),
        ]

        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                self.assertEqual(normalize_player_name(input_name), expected)

    def test_extract_goal_info(self):
        """Test goal information extraction."""
        test_cases = [
            {
                "title": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "expected": {
                    "score": "[3] - 1",
                    "minute": "81",
                    "scorer": "jesus"
                }
            },
            {
                "title": "Manchester United 2 - [3] Liverpool - Mo Salah 90+2'",
                "expected": {
                    "score": "2 - [3]",
                    "minute": "90",
                    "scorer": "salah"
                }
            },
            # Invalid cases
            {
                "title": "Match Thread: Arsenal vs Crystal Palace",
                "expected": None
            },
            {
                "title": "Post Match Thread: Arsenal 3-1 Crystal Palace",
                "expected": None
            }
        ]

        for case in test_cases:
            with self.subTest(title=case["title"]):
                result = extract_goal_info(case["title"])
                self.assertEqual(result, case["expected"])

    def test_duplicate_detection_exact_matches(self):
        """Test duplicate detection with exact matches."""
        test_cases = [
            # Same goal, different name formats
            {
                "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "title2": "Arsenal [3] - 1 Crystal Palace - G. Jesus 81'",
                "should_match": True,
                "time_diff": 30  # seconds
            },
            # Same goal, different score format
            {
                "title1": "Arsenal 3 - [2] Crystal Palace - Eddie Nketiah 85'",
                "title2": "Arsenal 3 - [2] Crystal Palace - E. Nketiah 85'",
                "should_match": True,
                "time_diff": 30
            }
        ]

        self._run_duplicate_tests(test_cases)

    def test_duplicate_detection_similar_minutes(self):
        """Test duplicate detection with similar minutes."""
        test_cases = [
            # Same goal, minute off by 1
            {
                "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "title2": "Arsenal [3] - 1 Crystal Palace - G. Jesus 82'",
                "should_match": True,
                "time_diff": 60
            },
            # Different goals, similar minutes
            {
                "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "title2": "Arsenal [3] - 1 Crystal Palace - Saka 82'",
                "should_match": False,
                "time_diff": 60
            }
        ]

        self._run_duplicate_tests(test_cases)

    def test_duplicate_detection_time_windows(self):
        """Test duplicate detection with different time windows."""
        test_cases = [
            # Same goal, just within time window
            {
                "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "title2": "Arsenal [3] - 1 Crystal Palace - G. Jesus 81'",
                "should_match": True,
                "time_diff": 59  # Just within 60s window
            },
            # Same goal, just outside time window
            {
                "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "title2": "Arsenal [3] - 1 Crystal Palace - G. Jesus 81'",
                "should_match": False,
                "time_diff": 61  # Just outside 60s window
            }
        ]

        self._run_duplicate_tests(test_cases)

    def test_duplicate_detection_different_goals(self):
        """Test duplicate detection with different goals."""
        test_cases = [
            # Different scorers
            {
                "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "title2": "Arsenal [3] - 1 Crystal Palace - Saka 81'",
                "should_match": False,
                "time_diff": 30
            },
            # Different scores
            {
                "title1": "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
                "title2": "Arsenal [4] - 1 Crystal Palace - Gabriel Jesus 81'",
                "should_match": False,
                "time_diff": 30
            }
        ]

        self._run_duplicate_tests(test_cases)

    def _run_duplicate_tests(self, test_cases):
        """Helper method to run duplicate detection tests."""
        for case in test_cases:
            with self.subTest(title1=case["title1"], title2=case["title2"]):
                # Clear previous test data
                self.posted_scores.clear()
                
                # Post first title
                current_time = self.base_time
                self.posted_scores[case["title1"]] = {
                    'timestamp': current_time,
                    'url': f'https://example.com/post1'
                }

                # Try to post second title after time_diff
                current_time = self.base_time + timedelta(seconds=case["time_diff"])
                is_duplicate = is_duplicate_score(
                    case["title2"],
                    self.posted_scores,
                    current_time,
                    url='https://example.com/post2'
                )

                self.assertEqual(
                    is_duplicate,
                    case["should_match"],
                    f"Expected duplicate={case['should_match']}, got {is_duplicate}"
                )

if __name__ == '__main__':
    unittest.main()
