"""Tests for update mode scheduling behavior."""

from poollab.const import (
    MANUAL_FALLBACK_INTERVAL,
    SCAN_INTERVAL,
    UPDATE_MODE_MANUAL,
    UPDATE_MODE_POLLING,
)
from poollab.coordinator import _get_update_interval_seconds


def test_update_mode_polling_uses_default_scan_interval():
    """Polling mode should keep the existing cloud polling interval."""
    assert _get_update_interval_seconds(UPDATE_MODE_POLLING) == SCAN_INTERVAL


def test_update_mode_manual_uses_twelve_hour_fallback_interval():
    """Manual mode should still refresh periodically as a safety net."""
    assert _get_update_interval_seconds(UPDATE_MODE_MANUAL) == MANUAL_FALLBACK_INTERVAL


def test_unknown_update_mode_falls_back_to_polling_interval():
    """Unknown option values should not break updates."""
    assert _get_update_interval_seconds("unexpected") == SCAN_INTERVAL
