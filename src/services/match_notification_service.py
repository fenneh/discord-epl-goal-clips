"""Match notification service for posting Premier League match updates."""

import os
from datetime import datetime, timezone
from typing import Dict, Set, Any, Optional, List

import aiohttp

from src.config import DISCORD_WEBHOOK_URL, DISCORD_USERNAME, DISCORD_AVATAR_URL, DATA_DIR
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

# Persistence files
MATCH_STATE_FILE = os.path.join(DATA_DIR, 'match_states.pkl')
DAILY_POSTED_FILE = os.path.join(DATA_DIR, 'daily_schedule_posted.pkl')
NOTIFIED_EVENTS_FILE = os.path.join(DATA_DIR, 'notified_events.pkl')

# Premier League logo for schedule posts
PL_LOGO = "https://resources.premierleague.com/premierleague/competitions/competition_1_small.png"


class MatchNotificationService:
    """Service for managing match notifications."""

    def __init__(self):
        # Track match states: {match_id: status}
        self.match_states: Dict[str, str] = load_data(MATCH_STATE_FILE, {})
        # Track which days we've posted schedule for: {date_str: True}
        self.daily_posted: Dict[str, bool] = load_data(DAILY_POSTED_FILE, {})
        # Track notified events: {match_id_event_type: True}
        self.notified_events: Set[str] = set(load_data(NOTIFIED_EVENTS_FILE, []))

    async def check_and_notify(self) -> None:
        """Main check method - called from periodic loop."""
        try:
            now_uk = get_current_uk_time()
            today_str = get_today_uk_date_str()

            # Check if 8am UK and haven't posted today's schedule
            if now_uk.hour == 8 and today_str not in self.daily_posted:
                await self._post_daily_schedule(today_str)

            # Check match state changes
            matches = await fetch_todays_matches()
            for match in matches:
                try:
                    await self._check_match_state(match)
                except Exception as e:
                    espn_logger.error(f"Error checking match {match.get('id')}: {e}")

        except Exception as e:
            espn_logger.error(f"Error in match notification check: {e}")

    async def _post_daily_schedule(self, date_str: str) -> None:
        """Post the daily schedule of matches."""
        try:
            matches = await fetch_todays_matches()
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

    async def _check_match_state(self, match: Dict[str, Any]) -> None:
        """Check for state changes and notify accordingly."""
        match_id = match.get('id')
        if not match_id:
            return

        current_status = match.get('status')
        previous_status = self.match_states.get(match_id)

        # Detect state transitions
        if previous_status != current_status:
            espn_logger.debug(f"Match {match_id} state change: {previous_status} -> {current_status}")

            # Kick-off: scheduled -> in progress
            if current_status == 'STATUS_IN_PROGRESS' and previous_status in (None, 'STATUS_SCHEDULED'):
                await self._notify_kickoff(match)

            # Full time: any -> full time
            elif current_status == 'STATUS_FULL_TIME' and previous_status != 'STATUS_FULL_TIME':
                await self._notify_final_score(match)

            # Update state
            self.match_states[match_id] = current_status
            save_data(self.match_states, MATCH_STATE_FILE)

    async def _notify_kickoff(self, match: Dict[str, Any]) -> None:
        """Send kick-off notification."""
        match_id = match.get('id')
        event_key = f"{match_id}_kickoff"

        if event_key in self.notified_events:
            return

        home_team = match.get('home_team', {})
        team_data = map_espn_team_to_config(home_team.get('name', ''))
        match_name = get_match_display_name(match)

        # Get team color and logo
        color = 0x00FF00  # Green for kick-off
        thumbnail_url = None
        if team_data and 'data' in team_data:
            color = team_data['data'].get('color', color)
            thumbnail_url = team_data['data'].get('logo')

        success = await self._post_embed(
            title="KICK-OFF",
            description=match_name,
            color=color,
            thumbnail_url=thumbnail_url,
        )

        if success:
            self.notified_events.add(event_key)
            save_data(list(self.notified_events), NOTIFIED_EVENTS_FILE)
            espn_logger.info(f"Posted kick-off: {match_name}")

    async def _notify_final_score(self, match: Dict[str, Any]) -> None:
        """Send final score notification."""
        match_id = match.get('id')
        event_key = f"{match_id}_fulltime"

        if event_key in self.notified_events:
            return

        home_team = match.get('home_team', {})
        team_data = map_espn_team_to_config(home_team.get('name', ''))
        score_display = get_match_score_display(match)

        # Get team color and logo
        color = 0x808080  # Gray default
        thumbnail_url = None
        if team_data and 'data' in team_data:
            color = team_data['data'].get('color', color)
            thumbnail_url = team_data['data'].get('logo')

        success = await self._post_embed(
            title="FULL TIME",
            description=score_display,
            color=color,
            thumbnail_url=thumbnail_url,
        )

        if success:
            self.notified_events.add(event_key)
            save_data(list(self.notified_events), NOTIFIED_EVENTS_FILE)
            espn_logger.info(f"Posted full time: {score_display}")

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
