"""Testy pro session manager (mock)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from config import MONICA_PANELS, MONICA_SELECTORS


def test_monica_panels_config():
    """Ověří, že MONICA_PANELS má správnou strukturu."""
    assert len(MONICA_PANELS) == 3
    required_keys = {"role", "model_label", "panel_index", "system_prefix"}
    for key, panel in MONICA_PANELS.items():
        assert key in ("claude", "gemini", "gpt")
        assert required_keys.issubset(panel.keys()), f"Missing keys in {key}"


def test_monica_selectors():
    """Ověří, že všechny CSS selektory jsou definovány."""
    required = ["layout_icons", "panel", "panel_title", "model_dropdown",
                "global_input", "global_send"]
    for sel in required:
        assert sel in MONICA_SELECTORS, f"Missing selector: {sel}"


def test_monica_roles():
    """Ověří role mozků."""
    roles = {p["role"] for p in MONICA_PANELS.values()}
    assert roles == {"architekt", "kreativní", "kritik"}


def test_rate_limiter_custom_delay():
    from utils.rate_limiter import RateLimiter
    limiter = RateLimiter(default_delay=5.0)
    limiter.set_delay("chatgpt", 1.0)
    assert limiter.custom_delays["chatgpt"] == 1.0
