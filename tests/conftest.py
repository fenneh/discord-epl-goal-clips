"""Test configuration and fixtures."""

from datetime import datetime, timezone

import pytest

import src.main as main

@pytest.fixture(autouse=True)
def isolate_runtime_state(monkeypatch):
    """Prevent tests from posting or writing files."""
    monkeypatch.setattr(main, "posted_urls", set())
    monkeypatch.setattr(main, "posted_scores", {})

    async def noop_async(*args, **kwargs):
        return True

    async def noop_none(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "post_to_discord", noop_async)
    monkeypatch.setattr(main, "post_mp4_link", noop_async)
    monkeypatch.setattr(main, "extract_mp4_with_retries", noop_none)
    monkeypatch.setattr(main, "save_data", lambda *args, **kwargs: None)

@pytest.fixture
def base_time():
    """Fixture for base timestamp."""
    return datetime.now(timezone.utc)

@pytest.fixture
def posted_scores():
    """Fixture for posted scores dictionary."""
    return {}
