"""Reddit service for fetching goal clips."""

import re
from typing import Optional, Dict, Any, List, overload, Literal, Union

import asyncpraw

from src.config import CLIENT_ID, CLIENT_SECRET, USER_AGENT
from src.config.teams import premier_league_teams
from src.services.video_service import video_extractor
from src.utils.logger import app_logger
from src.utils.url_utils import get_base_domain, get_domain_info

async def create_reddit_client() -> asyncpraw.Reddit:
    """Create and return a Reddit client instance.
    
    Returns:
        asyncpraw.Reddit: Authenticated Reddit client
    """
    return asyncpraw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
        requestor_kwargs={
            'timeout': 30  # Increase timeout to 30 seconds
        },
        check_for_updates=False,  # Disable update checks
        read_only=True  # Enable read-only mode since we only need to read
    )

@overload
def find_team_in_title(title: str, include_metadata: Literal[True]) -> Optional[Dict[str, Any]]: ...
@overload
def find_team_in_title(title: str, include_metadata: Literal[False] = ...) -> Optional[str]: ...
@overload
def find_team_in_title(title: str, include_metadata: bool = ...) -> Optional[Dict[str, Any] | str]: ...

def find_team_in_title(title: str, include_metadata: bool = False) -> Optional[Dict[str, Any] | str]:
    """Find Premier League team in post title.

    Args:
        title (str): Post title to search
        include_metadata (bool): If True, return team data dictionary, otherwise just team name

    Returns:
        Team name/data if found, None otherwise
    """
    if not title:
        return None
        
    # Clean and lowercase the title
    title_lower = title.lower()
    
    def check_team_match(text: str, team_name: str, team_data: dict) -> Optional[Union[str, Dict[str, Any]]]:
        """Helper function to check if a team matches in the given text."""
        team_name_lower = team_name.lower()
        aliases = [alias.lower() for alias in team_data.get('aliases', [])]

        if "newcastle jets" in text and team_name_lower in {"newcastle", "newcastle united"}:
            return None

        # Split text into words for exact matching
        text_words = text.split()
        text_phrases = [' '.join(text_words[i:i+4]) for i in range(len(text_words))]  # Check up to 4-word phrases
        
        # Create patterns with word boundaries
        team_patterns = [rf'\b{re.escape(name)}\b' for name in [team_name_lower] + aliases]
        
        # Try exact matches first
        for pattern in team_patterns:
            for phrase in text_phrases:
                if re.fullmatch(pattern, phrase):
                    if include_metadata:
                        return {
                            'name': team_name,
                            'data': team_data,
                            'is_scoring': None
                        }
                    return team_name
        
        # If no exact match, try word boundary matches
        for pattern in team_patterns:
            match = re.search(pattern, text)
            if match:
                # Additional check: make sure we don't match part of a longer word/phrase
                start, end = match.span()
                
                # Check character before match (if not at start)
                if start > 0 and text[start-1].isalnum():
                    continue
                    
                # Check character after match (if not at end)
                if end < len(text) and text[end].isalnum():
                    continue
                    
                if include_metadata:
                    return {
                        'name': team_name,
                        'data': team_data,
                        'is_scoring': None
                    }
                return team_name
        return None
        
    # Look for score patterns first
    score_patterns = [
        # More robust patterns allowing for different spacing and bracket positions
        r'^(.*?)\s*\[(\d+)\]\s*-\s*(\d+)\s*(.*?)$',  # Team1 [1] - 0 Team2
        r'^(.*?)\s*(\d+)\s*-\s*\[(\d+)\]\s*(.*?)$',  # Team1 0 - [1] Team2
        r'^(.*?)\s*\[(\d+)\s*-\s*(\d+)\]\s*(.*?)$',  # Team1 [1-0] Team2
        # r'^(.*?)\s*(\d+)\s*-\s*(\d+)\s*\[(.*)\]\s*-\' # Team1 1 - 0 [Team2 goal] - (Less common but possible)
        # Commenting out the potentially problematic pattern for now
    ]
    
    matched_pl_team_data = None # Store the first matched PL team data

    # Try score patterns first
    for pattern in score_patterns:
        match = re.search(pattern, title_lower, re.IGNORECASE)
        if match:
            app_logger.debug(f"Score pattern matched: {pattern}")
            groups = match.groups()
            
            # Extract teams based on pattern type
            if len(groups) == 4:
                 team1_str, score1, score2, team2_str = groups
            else: # Handle pattern with team name in brackets (less likely)
                # Adjust logic if needed based on exact pattern structure
                app_logger.warning(f"Unhandled score pattern group count: {len(groups)}")
                continue

            team1_str = team1_str.strip()
            team2_str = team2_str.strip()
            app_logger.debug(f"Extracted teams from score pattern: '{team1_str}' vs '{team2_str}'")
            
            # Determine which team likely scored based on bracket position in the *original* title
            # Find the first hyphen surrounded by spaces
            hyphen_match = re.search(r'\s+-\s+', title)
            if hyphen_match:
                split_point = hyphen_match.start()
                part1 = title[:split_point]
                part2 = title[split_point:]
                is_team1_scoring = '[' in part1 and ']' in part1
                is_team2_scoring = '[' in part2 and ']' in part2

                # Prefer the team string associated with the bracket
                scoring_team_str = team1_str if is_team1_scoring else team2_str

                # If brackets appear in both or neither part (e.g., [1-0]), scoring team is ambiguous here
                if is_team1_scoring == is_team2_scoring:
                    scoring_team_str = None # Cannot determine priority based on brackets
            else:
                 scoring_team_str = None # Cannot determine priority if standard hyphen separator not found

            # Check both extracted team strings against PL teams
            team1_match_data = None
            team2_match_data = None
            for team_name, team_data in premier_league_teams.items():
                 if not team1_match_data:
                     result = check_team_match(team1_str, team_name, team_data)
                     if result:
                         team1_match_data = result if isinstance(result, dict) else {'name': result, 'data': team_data, 'is_scoring': None}
                 if not team2_match_data:
                     result = check_team_match(team2_str, team_name, team_data)
                     if result:
                         team2_match_data = result if isinstance(result, dict) else {'name': result, 'data': team_data, 'is_scoring': None}
            
            # Determine final result based on matches and scoring priority
            if team1_match_data and team2_match_data:
                # Both are PL teams, prioritize based on scoring hint if available
                if scoring_team_str: # This implies hyphen_match was successful and is_team1_scoring/is_team2_scoring are set
                    if is_team1_scoring and not is_team2_scoring: # Team1 clearly scored
                        team1_match_data['is_scoring'] = True
                        team2_match_data['is_scoring'] = False
                        matched_pl_team_data = team1_match_data
                    elif is_team2_scoring and not is_team1_scoring: # Team2 clearly scored
                        team2_match_data['is_scoring'] = True
                        team1_match_data['is_scoring'] = False
                        matched_pl_team_data = team2_match_data
                    else:
                         # Ambiguous (e.g., brackets in both parts, or is_team1_scoring == is_team2_scoring was true earlier)
                         # or if scoring_team_str was None initially (though this 'if scoring_team_str:' check should prevent that here)
                         # Default to team1 if ambiguous here, or consider no definitive scoring team.
                         # For now, maintaining previous default-to-team1 behavior in ambiguity.
                         app_logger.debug("Scoring team ambiguous based on bracket analysis, defaulting to team1 if both PL.")
                         matched_pl_team_data = team1_match_data
                else:
                    # No scoring hint from hyphen analysis (scoring_team_str is None), default to first PL team found
                    app_logger.debug("No definitive scoring hint from hyphen analysis, defaulting to team1 if both PL.")
                    matched_pl_team_data = team1_match_data
            elif team1_match_data:
                 # Only team1 is a PL team, it's the one, scoring status depends on bracket hint if available
                 team1_match_data['is_scoring'] = scoring_team_str is not None and is_team1_scoring and not is_team2_scoring
                 matched_pl_team_data = team1_match_data
            elif team2_match_data:
                 # Only team2 is a PL team, it's the one, scoring status depends on bracket hint if available
                 team2_match_data['is_scoring'] = scoring_team_str is not None and is_team2_scoring and not is_team1_scoring
                 matched_pl_team_data = team2_match_data
            else:
                 app_logger.debug(f"Score pattern matched, but neither '{team1_str}' nor '{team2_str}' are recognized PL teams.")

            # If we found a PL team via score pattern, return it
            if matched_pl_team_data:
                 app_logger.debug(f"Found PL team via score pattern: {matched_pl_team_data['name']}")
                 return matched_pl_team_data if include_metadata else matched_pl_team_data['name']
            # else: continue searching other patterns or fallback

    # --- Fallback Logic --- 
    # If no score pattern yielded a PL team match, search the whole title BUT prioritize full names
    app_logger.debug("No PL team found via score patterns, trying fallback search.")
    found_teams = []
    for team_name, team_data in premier_league_teams.items():
        result = check_team_match(title_lower, team_name, team_data)
        if result:
            # Store the result (which might be dict or str)
            found_teams.append(result)

    if not found_teams:
        app_logger.debug("Fallback: No PL teams found in title.")
        return None
    
    # Prioritize matches based on full team name over aliases in fallback
    full_name_matches = []
    alias_matches = []
    for match_result in found_teams:
         team_name = match_result['name'] if isinstance(match_result, dict) else match_result
         team_data = premier_league_teams.get(team_name, {})
         # This requires check_team_match to indicate what specifically matched, 
         # or we compare the found team name against the title again
         # Simplification: Check if the main team name (not just alias) is in the title
         if re.search(rf'\b{re.escape(team_name.lower())}\b', title_lower):
             full_name_matches.append(match_result)
         else:
             # Check if it was potentially an alias match like 'United'
             # Be stricter: avoid short/ambiguous aliases in fallback
             is_ambiguous_alias = False
             raw_aliases = team_data.get('aliases', [])
             aliases: List[str] = [a.lower() for a in raw_aliases] if isinstance(raw_aliases, list) else []
             for alias in aliases:
                  # Example ambiguity check: alias is short and appears in title
                 if len(alias) <= 6 and re.search(rf'\b{re.escape(alias)}\b', title_lower):
                      # We need to know if THIS alias was the reason for the match in check_team_match
                      # This logic is imperfect without more info from check_team_match
                      # For now, we'll cautiously add it to alias_matches but prioritize full_name_matches
                      is_ambiguous_alias = True 
                      break # Found one potentially ambiguous alias
             if not is_ambiguous_alias:
                  alias_matches.append(match_result)
             else:
                  app_logger.debug(f"Fallback: Ignoring potentially ambiguous alias match for {team_name}")

    # Return the best match: prefer full name, then non-ambiguous alias
    if full_name_matches:
        best_match = full_name_matches[0] # Return first full name match
        app_logger.debug(f"Fallback: Returning full name match: {best_match['name'] if isinstance(best_match, dict) else best_match}")
        return best_match if include_metadata else (best_match['name'] if isinstance(best_match, dict) else best_match)
    elif alias_matches:
        best_match = alias_matches[0] # Return first non-ambiguous alias match
        app_logger.debug(f"Fallback: Returning alias match: {best_match['name'] if isinstance(best_match, dict) else best_match}")
        return best_match if include_metadata else (best_match['name'] if isinstance(best_match, dict) else best_match)
    else:
        app_logger.debug("Fallback: Only found ambiguous alias matches, returning None.")
        return None
            
    # return None # Original end of function if nothing found

async def extract_mp4_link(submission) -> Optional[str]:
    """Extract MP4 link from submission.
    
    Args:
        submission: Reddit submission object
        
    Returns:
        str: MP4 link if found, None otherwise
    """
    try:
        app_logger.info("=== Starting MP4 extraction ===")
        app_logger.info(f"Submission URL: {submission.url}")
        app_logger.info(f"Submission media: {submission.media}")
        
        # Get base domain
        base_domain = get_base_domain(submission.url)
        app_logger.info(f"Base domain: {base_domain}")
        
        # First check if submission URL is already an MP4
        if submission.url.endswith('.mp4'):
            app_logger.info("✓ Direct MP4 URL found")
            return submission.url
            
        # Check if it's a Reddit video
        if hasattr(submission, 'media') and submission.media:
            if 'reddit_video' in submission.media:
                app_logger.info("✓ Reddit video found")
                url = submission.media['reddit_video']['fallback_url']
                app_logger.info(f"Reddit video URL: {url}")
                return url
                
        # Use video extractor for supported base domains
        domain_info = get_domain_info(submission.url)
        matched_base = domain_info.get('matched_base') if domain_info else None

        if matched_base and domain_info:
            app_logger.info(f"Using video extractor for {domain_info.get('full_domain')} (base: {matched_base})")
            # Await the async call
            mp4_url = await video_extractor.extract_mp4_url(submission.url)
            if mp4_url:
                app_logger.info(f"✓ Found MP4 URL: {mp4_url}")
                return mp4_url
            else:
                app_logger.warning(f"Video extractor failed to find MP4 URL for: {submission.url}")
        else:
             app_logger.debug(f"Domain not supported by video extractor: {domain_info.get('full_domain') if domain_info else 'Unknown'}")
                
        app_logger.warning(f"No MP4 URL found for submission: {submission.url}")
        return None
            
    except Exception as e:
        app_logger.error(f"Error extracting MP4 link: {str(e)}", exc_info=True)
        return None
