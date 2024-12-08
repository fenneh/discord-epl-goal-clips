import unittest
from datetime import datetime, timezone
import sys
import os
import re

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from goal_bot import normalize_score_pattern, is_duplicate_score, posted_scores

# List of Premier League teams and their aliases
premier_league_teams = {
    "Arsenal": ["The Gunners"],
    "Aston Villa": [],
    "Bournemouth": [],
    "Brentford": [],
    "Brighton & Hove Albion": [],
    "Chelsea": ["The Blues"],
    "Crystal Palace": ["The Eagles"],
    "Everton": ["The Toffees"],
    "Fulham": ["The Cottagers"],
    "Leeds United": ["The Whites"],
    "Leicester City": ["The Foxes"],
    "Liverpool": ["The Reds"],
    "Manchester City": ["The Citizens"],
    "Manchester United": ["The Red Devils"],
    "Newcastle United": ["The Magpies"],
    "Nottingham Forest": ["The Reds"],
    "Southampton": ["The Saints"],
    "Tottenham Hotspur": ["Spurs"],
    "West Ham United": ["The Hammers"],
    "Wolverhampton Wanderers": ["Wolves"],
}

def contains_premier_league_team(title):
    """Check if a title contains a Premier League team name or alias"""
    title = title.lower()
    for team, aliases in premier_league_teams.items():
        team = team.lower()
        if re.search(r"\b" + re.escape(team) + r"\b", title):
            return True
        for alias in aliases:
            alias = alias.lower()
            if re.search(r"\b" + re.escape(alias) + r"\b", title):
                return True
    return False

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

class TestPremierLeagueTeams(unittest.TestCase):
    def test_exact_matches(self):
        """Test exact team name matches"""
        test_cases = [
            ("Arsenal score a goal!", True),
            ("Manchester United win 2-0", True),
            ("Chelsea vs Liverpool", True),
            ("Random text without team", False),
        ]
        for title, expected in test_cases:
            with self.subTest(title=title):
                self.assertEqual(contains_premier_league_team(title), expected)

    def test_partial_matches(self):
        """Test that partial matches don't trigger false positives"""
        test_cases = [
            ("Arsenalistas win the game", False),
            ("Liverpoolian culture", False),
            ("Chelseafc.com", False),
            ("Manchesterford", False),
        ]
        for title, expected in test_cases:
            with self.subTest(title=title):
                self.assertEqual(contains_premier_league_team(title), expected)

    def test_team_aliases(self):
        """Test that team aliases are properly recognized"""
        test_cases = [
            ("The Gunners take the lead", True),  # Arsenal alias
            ("The Red Devils score", True),       # Man United alias
            ("The Blues equalize", True),         # Chelsea alias
            ("Random Devils in the title", False) # Shouldn't match partial alias
        ]
        for title, expected in test_cases:
            with self.subTest(title=title):
                self.assertEqual(contains_premier_league_team(title), expected)

    def test_case_insensitivity(self):
        """Test that matching is case insensitive"""
        test_cases = [
            ("ARSENAL GOAL!", True),
            ("arsenal score", True),
            ("ArSeNaL win", True),
            ("The GUNNERS celebrate", True),
        ]
        for title, expected in test_cases:
            with self.subTest(title=title):
                self.assertEqual(contains_premier_league_team(title), expected)

    def test_word_boundaries(self):
        """Test that word boundaries are respected"""
        test_cases = [
            ("Arsenal vs Chelsea", True),
            ("Arsenal's goal", True),
            ("Arsenal-Chelsea", True),
            ("Arsenal/Chelsea matchday", True),
            ("ArsenalChelsea", False),  # No word boundary
            ("xArsenalx", False),       # No word boundary
        ]
        for title, expected in test_cases:
            with self.subTest(title=title):
                self.assertEqual(contains_premier_league_team(title), expected)

if __name__ == '__main__':
    unittest.main()
