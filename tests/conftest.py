"""Test configuration and fixtures."""

import pytest
from datetime import datetime, timezone

@pytest.fixture
def base_time():
    """Fixture for base timestamp."""
    return datetime.now(timezone.utc)

@pytest.fixture
def posted_scores():
    """Fixture for posted scores dictionary."""
    return {}
