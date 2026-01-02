"""Match notification service for posting Premier League match updates."""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Set, Any, Optional, List

import aiohttp

from src.config import DISCORD_WEBHOOK_URL, DISCORD_USERNAME, DISCORD_AVATAR_URL, DATA_DIR, POSTED_SCORES_FILE
from src.services.espn_service import fetch_todays_matches, get_match_display_name, get_match_score_display, espn_logger
from src.utils.match_utils import (
    map_espn_team_to_config,
    format_match_time_uk,
    get_current_uk_time,
    get_today_uk_date_str,
    UK_TZ,
    PL_COLOR,
)
from src.utils.persistence import save_data, load_data
from src.utils.logger import webhook_logger
from src.utils.score_utils import normalize_team_name

# Persistence files
MATCH_STATE_FILE = os.path.join(DATA_DIR, 'match_states.pkl')
DAILY_POSTED_FILE = os.path.join(DATA_DIR, 'daily_schedule_posted.pkl')
NOTIFIED_EVENTS_FILE = os.path.join(DATA_DIR, 'notified_events.pkl')
KNOWN_GOALS_FILE = os.path.join(DATA_DIR, 'known_goals.pkl')
PENDING_GOALS_FILE = os.path.join(DATA_DIR, 'pending_goals.pkl')

# Premier League logo for schedule posts
PL_LOGO = "https://resources.premierleague.com/premierleague/competitions/competition_1_small.png"

# Goal fallback timing
GOAL_FALLBACK_SECONDS = 30  # Wait this long for Reddit before posting ESPN fallback


class MatchNotificationService:
    """Service for managing match notifications."""

    def __init__(self):
        # Track match states: {match_id: status}
        self.match_states: Dict[str, str] = load_data(MATCH_STATE_FILE, {})
        # Track which days we've posted schedule for: {date_str: True}
        self.daily_posted: Dict[str, bool] = load_data(DAILY_POSTED_FILE, {})
        # Track notified events: {match_id_event_type: True}
        self.notified_events: Set[str] = set(load_data(NOTIFIED_EVENTS_FILE, []))
        # Track known goals per match: {match_id: [goal_keys]}
        self.known_goals: Dict[str, List[str]] = load_data(KNOWN_GOALS_FILE, {})
        # Track pending goals waiting for Reddit: {goal_key: {data}}
        self.pending_goals: Dict[str, Dict[str, Any]] = load_data(PENDING_GOALS_FILE, {})

    async def check_and_notify(self) -> None:
        """Main check method - called from periodic loop."""
        try:
            now_uk = get_current_uk_time()
            today_str = get_today_uk_date_str()

            # Check if 8am UK and haven't posted today's schedule
            if now_uk.hour == 8 and today_str not in self.daily_posted:
                await self._post_daily_schedule(today_str)

            # Check match state changes and goals
            matches = fetch_todays_matches()
            espn_logger.info(f"ESPN check: found {len(matches)} matches")

            # Check for kick-offs based on scheduled time
            await self._check_kickoffs_by_time(matches)

            for match in matches:
                try:
                    # Check for full-time
                    await self._check_for_fulltime(match)
                    # Check for goals
                    await self._check_for_goals(match)
                except Exception as e:
                    espn_logger.error(f"Error checking match {match.get('id')}: {e}")

            # Process pending goals (post fallback if Reddit didn't cover them)
            await self._process_pending_goals()

        except Exception as e:
            espn_logger.error(f"Error in match notification check: {e}")

    async def _post_daily_schedule(self, date_str: str) -> None:
        """Post the daily schedule of matches."""
        try:
            matches = fetch_todays_matches()
            if not matches:
                espn_logger.info(f"No matches scheduled for {date_str}")
                # Still mark as posted to avoid repeated API calls
                self.daily_posted[date_str] = True
                save_data(self.daily_posted, DAILY_POSTED_FILE)
                return

            # Format schedule
            schedule_lines = []
            for match in sorted(matches, key=lambda m: m.get('date', '')):
                kick_off = format_match_time_uk(match.get('date', ''))
                match_name = get_match_display_name(match)
                schedule_lines.append(f"**{kick_off}** - {match_name}")

            description = '\n'.join(schedule_lines)

            # Format date nicely
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = dt.strftime('%-d %b %Y')
            except Exception:
                formatted_date = date_str

            # Post to Discord
            success = await self._post_embed(
                title=f"Premier League - {formatted_date}",
                description=description,
                color=PL_COLOR,
                thumbnail_url=PL_LOGO,
            )

            if success:
                self.daily_posted[date_str] = True
                save_data(self.daily_posted, DAILY_POSTED_FILE)
                espn_logger.info(f"Posted daily schedule for {date_str}")

        except Exception as e:
            espn_logger.error(f"Error posting daily schedule: {e}")

    def _parse_match_time(self, date_str: str) -> Optional[datetime]:
        """Parse ESPN date string to datetime."""
        if not date_str:
            return None
        try:
            # Handle both Z suffix and +00:00 format
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str)
        except Exception:
            return None

    async def _check_kickoffs_by_time(self, matches: List[Dict[str, Any]]) -> None:
        """Check for kick-offs based on scheduled time and post batched by time slot."""
        now = datetime.now(timezone.utc)

        # Group matches by scheduled time that should have kicked off
        time_slots: Dict[str, List[Dict[str, Any]]] = {}

        for match in matches:
            match_id = match.get('id')
            if not match_id:
                continue

            event_key = f"{match_id}_kickoff"
            if event_key in self.notified_events:
                continue

            # Get scheduled time
            scheduled_time = self._parse_match_time(match.get('date'))
            if not scheduled_time:
                continue

            # Check if kick-off time has passed but match hasn't ended
            status = match.get('status')
            if now >= scheduled_time and status != 'STATUS_FULL_TIME':
                # Use the scheduled time as the grouping key
                time_key = scheduled_time.isoformat()
                if time_key not in time_slots:
                    time_slots[time_key] = []
                time_slots[time_key].append(match)

        # Post one notification per time slot
        for time_key, slot_matches in time_slots.items():
            await self._notify_kickoffs_batched(slot_matches)

    async def _notify_kickoffs_batched(self, matches: List[Dict[str, Any]]) -> None:
        """Send batched kick-off notification for matches at the same time."""
        if not matches:
            return

        # Build description with all matches
        match_names = [get_match_display_name(m) for m in matches]
        description = '\n'.join(match_names)

        # Use singular or plural title
        title = "KICK-OFF" if len(matches) == 1 else "KICK-OFFS"

        success = await self._post_embed(
            title=title,
            description=description,
            color=0x00FF00,  # Green for kick-off
        )

        if success:
            for match in matches:
                match_id = match.get('id')
                event_key = f"{match_id}_kickoff"
                self.notified_events.add(event_key)
            save_data(list(self.notified_events), NOTIFIED_EVENTS_FILE)
            espn_logger.info(f"Posted kick-offs: {', '.join(match_names)}")

    async def _check_for_fulltime(self, match: Dict[str, Any]) -> None:
        """Check if match has ended and notify."""
        match_id = match.get('id')
        if not match_id:
            return

        current_status = match.get('status')
        previous_status = self.match_states.get(match_id)

        # Detect full-time
        if current_status == 'STATUS_FULL_TIME' and previous_status != 'STATUS_FULL_TIME':
            espn_logger.info(f"Match {match_id} ended: {previous_status} -> {current_status}")
            await self._notify_final_score(match)

        # Update state if changed
        if previous_status != current_status:
            self.match_states[match_id] = current_status
            save_data(self.match_states, MATCH_STATE_FILE)

    async def _notify_final_score(self, match: Dict[str, Any]) -> None:
        """Send final score notification."""
        match_id = match.get('id')
        event_key = f"{match_id}_fulltime"

        if event_key in self.notified_events:
            return

        score_display = get_match_score_display(match)

        success = await self._post_embed(
            title="FULL TIME",
            description=score_display,
            color=0x808080,  # Gray
        )

        if success:
            self.notified_events.add(event_key)
            save_data(list(self.notified_events), NOTIFIED_EVENTS_FILE)
            espn_logger.info(f"Posted full time: {score_display}")

    async def _check_for_goals(self, match: Dict[str, Any]) -> None:
        """Check for new goals in a match and add to pending if not covered by Reddit."""
        match_id = match.get('id')
        if not match_id:
            return

        # Only check for goals in live matches
        status = match.get('status')
        if status not in ('STATUS_FIRST_HALF', 'STATUS_SECOND_HALF', 'STATUS_HALFTIME'):
            return

        home_team = match.get('home_team', {})
        away_team = match.get('away_team', {})
        home_name = home_team.get('name', 'Unknown')
        away_name = away_team.get('name', 'Unknown')
        home_score = home_team.get('score', '0')
        away_score = away_team.get('score', '0')

        # Get goals from match data
        goals = match.get('goals', [])
        if not goals:
            return

        # Initialize known goals for this match if needed
        if match_id not in self.known_goals:
            self.known_goals[match_id] = []

        for goal in goals:
            try:
                goal_key = self._generate_goal_key(match, goal)
                if not goal_key:
                    continue

                # Skip if we already know about this goal
                if goal_key in self.known_goals[match_id]:
                    continue

                # New goal detected!
                espn_logger.info(f"New goal detected: {goal_key}")

                # Add to known goals
                self.known_goals[match_id].append(goal_key)
                save_data(self.known_goals, KNOWN_GOALS_FILE)

                # Add to pending goals (wait for Reddit)
                self.pending_goals[goal_key] = {
                    'detected_at': datetime.now(timezone.utc).isoformat(),
                    'match_id': match_id,
                    'home_team': home_name,
                    'away_team': away_name,
                    'home_score': home_score,
                    'away_score': away_score,
                    'scorer': goal.get('scorer', 'Unknown'),
                    'minute': goal.get('minute', ''),
                    'scoring_team': goal.get('team', ''),
                }
                save_data(self.pending_goals, PENDING_GOALS_FILE)
                espn_logger.info(f"Added goal to pending: {goal_key}")

            except Exception as e:
                espn_logger.error(f"Error processing goal: {e}")

    def _generate_goal_key(self, match: Dict[str, Any], goal: Dict[str, Any]) -> Optional[str]:
        """Generate a canonical key for a goal event.

        Format: {team1}_vs_{team2}_{score}_{minute}
        Teams are normalized and sorted alphabetically.
        """
        try:
            home_team = match.get('home_team', {})
            away_team = match.get('away_team', {})
            home_name = normalize_team_name(home_team.get('name', ''))
            away_name = normalize_team_name(away_team.get('name', ''))
            home_score = home_team.get('score', '0')
            away_score = away_team.get('score', '0')
            minute = goal.get('minute', '').split('+')[0]  # Base minute only

            if not home_name or not away_name or not minute:
                return None

            # Sort teams alphabetically for consistency
            teams_key = "_vs_".join(sorted([home_name, away_name]))
            score_key = f"{home_score}-{away_score}"

            return f"{teams_key}_{score_key}_{minute}"

        except Exception as e:
            espn_logger.error(f"Error generating goal key: {e}")
            return None

    async def _process_pending_goals(self) -> None:
        """Process pending goals and post fallback if Reddit didn't cover them."""
        if not self.pending_goals:
            return

        now = datetime.now(timezone.utc)
        posted_scores = load_data(POSTED_SCORES_FILE, {})
        goals_to_remove = []

        for goal_key, goal_data in self.pending_goals.items():
            try:
                detected_at = datetime.fromisoformat(goal_data['detected_at'])
                elapsed = (now - detected_at).total_seconds()

                # Check if Reddit has posted this goal
                if self._reddit_posted_goal(goal_key, posted_scores):
                    espn_logger.info(f"Reddit covered goal: {goal_key}")
                    goals_to_remove.append(goal_key)
                    continue

                # Wait for fallback window
                if elapsed < GOAL_FALLBACK_SECONDS:
                    continue

                # Reddit didn't post within window - post ESPN fallback
                espn_logger.info(f"Reddit didn't cover goal after {GOAL_FALLBACK_SECONDS}s, posting fallback: {goal_key}")
                await self._post_goal_fallback(goal_data)
                goals_to_remove.append(goal_key)

            except Exception as e:
                espn_logger.error(f"Error processing pending goal {goal_key}: {e}")
                # Remove problematic entries to avoid infinite loops
                goals_to_remove.append(goal_key)

        # Clean up processed goals
        for key in goals_to_remove:
            if key in self.pending_goals:
                del self.pending_goals[key]

        if goals_to_remove:
            save_data(self.pending_goals, PENDING_GOALS_FILE)

    def _reddit_posted_goal(self, goal_key: str, posted_scores: Dict[str, Dict]) -> bool:
        """Check if Reddit has posted a matching goal.

        Uses fuzzy matching on the canonical key with minute tolerance.
        """
        if not posted_scores:
            return False

        # Parse the goal key
        parts = goal_key.rsplit('_', 2)  # teams_key, score, minute
        if len(parts) != 3:
            return False

        teams_key, score, minute = parts

        try:
            goal_minute = int(minute)
        except ValueError:
            return False

        # Check for matching Reddit posts with minute tolerance
        for reddit_key in posted_scores.keys():
            reddit_parts = reddit_key.rsplit('_', 2)
            if len(reddit_parts) != 3:
                continue

            reddit_teams, reddit_score, reddit_minute = reddit_parts

            # Check teams match
            if reddit_teams != teams_key:
                continue

            # Check score matches
            if reddit_score != score:
                continue

            # Check minute within tolerance (±2 minutes)
            try:
                reddit_min = int(reddit_minute)
                if abs(reddit_min - goal_minute) <= 2:
                    return True
            except ValueError:
                continue

        return False

    async def _post_goal_fallback(self, goal_data: Dict[str, Any]) -> None:
        """Post ESPN goal fallback notification."""
        home_team = goal_data.get('home_team', 'Unknown')
        away_team = goal_data.get('away_team', 'Unknown')
        home_score = goal_data.get('home_score', '0')
        away_score = goal_data.get('away_score', '0')
        scorer = goal_data.get('scorer', 'Unknown')
        minute = goal_data.get('minute', '')
        scoring_team = goal_data.get('scoring_team', '')

        # Get team branding for scoring team
        team_data = map_espn_team_to_config(scoring_team)

        # Format description
        score_line = f"{home_team} {home_score} - {away_score} {away_team}"
        scorer_line = f"{scorer} {minute}'" if minute else scorer
        description = f"{score_line}\n{scorer_line}"

        # Get team color and logo
        color = 0x00FF00  # Green for goal
        thumbnail_url = None
        if team_data and 'data' in team_data:
            color = team_data['data'].get('color', color)
            thumbnail_url = team_data['data'].get('logo')

        await self._post_embed(
            title="GOAL!",
            description=description,
            color=color,
            thumbnail_url=thumbnail_url,
        )

    async def _post_embed(
        self,
        title: str,
        description: str,
        color: int = 0x808080,
        thumbnail_url: Optional[str] = None,
    ) -> bool:
        """Post an embed to Discord webhook.

        Args:
            title: Embed title
            description: Embed description
            color: Embed color (hex int)
            thumbnail_url: Optional thumbnail image URL

        Returns:
            True if successful, False otherwise
        """
        if not DISCORD_WEBHOOK_URL:
            webhook_logger.error("Discord webhook URL not configured")
            return False

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}

        webhook_data = {
            "username": DISCORD_USERNAME,
            "avatar_url": DISCORD_AVATAR_URL,
            "embeds": [embed],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(DISCORD_WEBHOOK_URL, json=webhook_data) as response:
                    if response.status == 429:
                        webhook_logger.warning(
                            f"Rate limited by Discord. Retry after: {response.headers.get('Retry-After', 'unknown')} seconds"
                        )
                        return False

                    if response.status != 204:
                        response_text = await response.text()
                        webhook_logger.error(
                            f"Failed to post to Discord. Status: {response.status}, Response: {response_text}"
                        )
                        return False

                    webhook_logger.info(f"Successfully posted embed: {title}")
                    return True

        except Exception as e:
            webhook_logger.error(f"Error posting embed to Discord: {e}")
            return False

    def cleanup_old_states(self, days: int = 7) -> None:
        """Clean up old match states and notified events.

        Args:
            days: Remove states older than this many days
        """
        # For now, just clear old daily_posted entries
        today = get_today_uk_date_str()
        old_keys = [k for k in self.daily_posted.keys() if k < today]
        for key in old_keys:
            del self.daily_posted[key]
        if old_keys:
            save_data(self.daily_posted, DAILY_POSTED_FILE)
            espn_logger.debug(f"Cleaned up {len(old_keys)} old daily_posted entries")


# Global service instance
match_notification_service = MatchNotificationService()
