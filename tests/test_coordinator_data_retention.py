"""Tests for retaining coordinator data when API returns empty updates."""

import pytest

from poollab.coordinator import PoollabDataUpdateCoordinator


class _ApiReturnsNoMeasurements:
    """API stub returning no measurements."""

    async def get_measurements(self):
        return []


class _ApiReturnsOtherDeviceMeasurements:
    """API stub returning measurements for a different device."""

    async def get_measurements(self):
        return [
            {
                "account": "other-device",
                "device_serial": "other-serial",
                "parameter": "PL pH",
                "value": 7.2,
                "timestamp": "2026-07-01T12:00:00Z",
            }
        ]


@pytest.mark.asyncio
async def test_keeps_last_successful_data_when_measurements_list_is_empty():
    """Coordinator should not clear entities when backend temporarily returns no data."""
    coordinator = PoollabDataUpdateCoordinator(
        hass=object(),
        api_client=_ApiReturnsNoMeasurements(),
        device_id="device-1",
    )
    coordinator.data = {
        "device_id": "device-1",
        "measurements": [{"parameter": "PL pH", "value": 7.1}],
        "latest_values": {"PL pH": {"value": 7.1, "timestamp": "2026-07-01T08:00:00Z"}},
        "measurement_counts": {"PL pH": 1},
        "active_chlorine": {},
        "invalid_measurement_count": 0,
        "last_measurement_time": "2026-07-01T08:00:00Z",
    }

    result = await coordinator._async_update_data()

    assert result is coordinator.data
    assert result["latest_values"]["PL pH"]["value"] == 7.1


@pytest.mark.asyncio
async def test_keeps_last_successful_data_when_device_has_no_matching_measurements():
    """Coordinator should retain previous state when API data omits this device."""
    coordinator = PoollabDataUpdateCoordinator(
        hass=object(),
        api_client=_ApiReturnsOtherDeviceMeasurements(),
        device_id="device-1",
    )
    coordinator.data = {
        "device_id": "device-1",
        "measurements": [{"parameter": "PL Chlorine Free", "value": 2.0}],
        "latest_values": {
            "PL Chlorine Free": {"value": 2.0, "timestamp": "2026-07-01T09:00:00Z"}
        },
        "measurement_counts": {"PL Chlorine Free": 1},
        "active_chlorine": {},
        "invalid_measurement_count": 0,
        "last_measurement_time": "2026-07-01T09:00:00Z",
    }

    result = await coordinator._async_update_data()

    assert result is coordinator.data
    assert result["latest_values"]["PL Chlorine Free"]["value"] == 2.0
