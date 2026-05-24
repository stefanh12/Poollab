"""Timestamp helpers for Poollab measurements."""

from datetime import datetime, timezone


def _local_timezone():
    """Return the system local timezone, falling back to UTC if unavailable."""
    return datetime.now().astimezone().tzinfo or timezone.utc


def parse_measurement_timestamp(raw_ts, assume_timezone=None):
    """Parse a measurement timestamp into a timezone-aware datetime.

    Numeric timestamps are treated as unix epoch seconds or milliseconds.
    Naive ISO strings are assumed to be in the provided timezone, or the
    system local timezone when none is supplied.
    """
    if raw_ts is None:
        return None

    timezone_to_use = assume_timezone or _local_timezone()

    try:
        if isinstance(raw_ts, (int, float)):
            ts = float(raw_ts)
            ts = ts / 1000.0 if ts > 1e12 else ts
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        ts_str = str(raw_ts).strip()
        if ts_str.isdigit():
            ts = float(ts_str)
            ts = ts / 1000.0 if ts > 1e12 else ts
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone_to_use)
        return dt
    except (ValueError, TypeError, OSError):
        return None


def measurement_timestamp_sort_key(measurement, assume_timezone=None):
    """Return a sortable timestamp key for a measurement."""
    parsed = parse_measurement_timestamp(measurement.get("timestamp"), assume_timezone)
    return parsed.timestamp() if parsed else 0.0
