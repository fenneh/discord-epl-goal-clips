"""Tests for post processing functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from src.main import contains_goal_keyword, contains_excluded_term, process_submission


class MockSubmission:
    """Mock Reddit submission for testing."""

    def __init__(self, title: str, url: str, created_utc: float):
        self.title = title
        self.url = url
        self.created_utc = created_utc
        self.permalink = f"/r/soccer/comments/test/{title.replace(' ', '_')[:20]}"


@pytest.mark.parametrize(
    "title,should_match",
    [
        # Standard formats
        ("Arsenal [1] - 0 Chelsea", True),
        ("Chelsea 0 - [1] Arsenal", True),
        ("Arsenal [1-0] Chelsea", True),
        # Goal variations
        ("GOAL! Arsenal 1-0 Chelsea", True),
        ("⚽ Arsenal 1-0 Chelsea", True),
        ("Great Goal! Arsenal 1-0 Chelsea", True),
        # Non-goal posts
        ("Match Thread: Arsenal vs Chelsea", False),
        ("Post Match Thread: Arsenal 1-0 Chelsea", False),
        ("Half Time: Arsenal 0-0 Chelsea", False),
    ],
)
def test_goal_keyword_detection(title: str, should_match: bool):
    """Test detection of goal-related keywords."""
    assert contains_goal_keyword(title) == should_match


@pytest.mark.parametrize(
    "title,should_exclude",
    [
        # Excluded terms
        ("Pre-Match Thread: Arsenal vs Chelsea", True),
        ("Match Thread: Arsenal vs Chelsea", True),
        ("Post Match Thread: Arsenal 1-0 Chelsea", True),
        ("Half Time: Arsenal 0-0 Chelsea", True),
        # Valid goal posts
        ("Arsenal [1] - 0 Chelsea", False),
        ("Chelsea 0 - [1] Arsenal", False),
        ("GOAL! Arsenal 1-0 Chelsea", False),
    ],
)
def test_excluded_term_detection(title: str, should_exclude: bool):
    """Test detection of excluded terms."""
    assert contains_excluded_term(title) == should_exclude


@pytest.mark.asyncio
async def test_old_post_rejection():
    """Test that old posts are rejected."""
    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(minutes=10)).timestamp()

    submission = MockSubmission(
        title="Arsenal [1] - 0 Chelsea", url="https://example.com", created_utc=old_time
    )

    result = await process_submission(submission)
    assert result is False, "Old post should be rejected"


@pytest.mark.asyncio
async def test_recent_post_processing():
    """Test that recent posts are processed."""
    now = datetime.now(timezone.utc)
    recent_time = (now - timedelta(minutes=2)).timestamp()

    submission = MockSubmission(
        title="Arsenal [1] - 0 Chelsea",
        url="https://streamff.com/v/123",
        created_utc=recent_time,
    )

    result = await process_submission(submission)
    assert result is True, "Recent post should be processed"


@pytest.mark.parametrize(
    "title",
    [
        "Match Thread: Arsenal vs Chelsea",
        "Post Match Thread: Arsenal 1-0 Chelsea",
        "Pre Match Thread: Arsenal vs Chelsea",
        "Half Time: Arsenal 0-0 Chelsea",
    ],
)
@pytest.mark.asyncio
async def test_non_goal_post_rejection(title: str):
    """Test that non-goal posts are rejected."""
    now = datetime.now(timezone.utc)
    submission = MockSubmission(
        title=title, url="https://example.com", created_utc=now.timestamp()
    )

    result = await process_submission(submission)
    assert result is False, f"Non-goal post should be rejected: {title}"


@pytest.mark.parametrize(
    "url,should_process",
    [
        ("https://streamff.com/v/123", True),
        ("https://streamin.me/v/123", True),
        ("https://dubz.co/v/123", True),
        ("https://youtube.com/watch?v=123", False),
        ("https://twitter.com/status/123", False),
    ],
)
@pytest.mark.asyncio
async def test_url_domain_filtering(url: str, should_process: bool):
    """Test filtering of posts based on URL domain."""
    now = datetime.now(timezone.utc)
    submission = MockSubmission(
        title="Arsenal [1] - 0 Chelsea", url=url, created_utc=now.timestamp()
    )

    result = await process_submission(submission)
    assert result == should_process, f"URL domain filtering failed for: {url}"
