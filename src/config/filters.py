"""Configuration for post filtering."""

# Keywords to identify goal posts
goal_keywords = [
    "goal", 
    "scores", 
    "scored", 
    r"\d{1,3}'",  # Matches minute markers like 45'
    r"\[\d+\]\s*-\s*\d+",  # Matches [5] - 2
    r"\d+\s*-\s*\[\d+\]",  # Matches 2 - [5]
]

# Terms to exclude from posts (e.g., women's football, youth games)
excluded_terms = [
    r'\bW\b',  # Matches standalone W
    r'\bU19\b',  # Matches U19
]

# Specific websites to match URLs
streamin_domains = [
    "streamin.one", 
    "streamin.me", 
    "streamin.pro", 
    "streamin.live", 
    "streamin.cc", 
    "streamin.xyz"
]

specific_sites = ["streamff.co"] + streamin_domains + ["dubz.link"]
