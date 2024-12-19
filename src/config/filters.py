"""Filter configurations for goal detection."""

from src.utils.keywords import GOAL_KEYWORDS, EXCLUDED_TERMS

# Legacy patterns (to be removed)
goal_keywords = [
    r'goal',
    r'score[ds]?',
    r'strike',
    r'finish',
    r'tap in',
    r'header',
    r'penalty',
    r'free kick',
    r'volley'
]

excluded_terms = [
    r'match thread',
    r'post match',
    r'pre match',
    r'match report',
    r'half time',
    r'lineup',
    r'line up',
    r'team news',
    r'injury',
    r'injured',
    r'transfer',
    r'signs',
    r'loan',
    r'rumour',
    r'rumor',
    r'update',
    r'news',
    r'official'
]

# Base domains for supported video sites
base_domains = {
    'dubz',
    'streamff',
    'streamin',
    'streamable',
    'streamja',
    'streamvi',
    'streamwo',
    'streamye',
    'streamgg'
}
