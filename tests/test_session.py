"""Testy pro session manager (mock)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from session_manager import AISession
from utils.rate_limiter import RateLimiter


@pytest.fixture
def mock_session():
    limiter = RateLimiter(default_delay=0)
    session = AISession("chatgpt", limiter)
    session.is_connected = True
    session.page = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_session_not_connected():
    limiter = RateLimiter()
    session = AISession("chatgpt", limiter)
    with pytest.raises(ConnectionError):
        await session.send_message("test")


def test_rate_limiter_custom_delay():
    limiter = RateLimiter(default_delay=5.0)
    limiter.set_delay("chatgpt", 1.0)
    assert limiter.custom_delays["chatgpt"] == 1.0
