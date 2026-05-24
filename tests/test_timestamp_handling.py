"""Tests for Poollab measurement timestamp handling."""

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from poollab.time_utils import measurement_timestamp_sort_key, parse_measurement_timestamp


def test_parse_measurement_timestamp_assumes_local_timezone_for_naive_iso():
    """Naive ISO timestamps should keep the local wall clock time."""
    stockholm = ZoneInfo("Europe/Stockholm")

    parsed = parse_measurement_timestamp("2026-06-01T12:30:00", assume_timezone=stockholm)

    assert parsed is not None
    assert parsed.tzinfo == stockholm
    assert parsed.hour == 12
    assert parsed.minute == 30
    assert parsed.utcoffset() == timedelta(hours=2)


def test_parse_measurement_timestamp_preserves_utc_suffix():
    """Z-suffixed ISO timestamps should stay in UTC."""
    parsed = parse_measurement_timestamp("2026-06-01T12:30:00Z")

    assert parsed is not None
    assert parsed.tzinfo == timezone.utc
    assert parsed.hour == 12
    assert parsed.minute == 30


def test_parse_measurement_timestamp_supports_epoch_seconds_and_milliseconds():
    """Epoch timestamps should be parsed as absolute instants."""
    seconds = parse_measurement_timestamp(1_717_244_200)
    milliseconds = parse_measurement_timestamp(1_717_244_200_000)

    assert seconds is not None
    assert milliseconds is not None
    assert seconds == milliseconds
    assert seconds.tzinfo == timezone.utc


def test_measurement_timestamp_sort_key_uses_parsed_instant():
    """Sort keys should order by the actual instant, not the raw string."""
    stockholm = ZoneInfo("Europe/Stockholm")

    earlier = measurement_timestamp_sort_key(
        {"timestamp": "2026-06-01T12:00:00"},
        assume_timezone=stockholm,
    )
    later = measurement_timestamp_sort_key(
        {"timestamp": "2026-06-01T13:00:00"},
        assume_timezone=stockholm,
    )

    assert later > earlier