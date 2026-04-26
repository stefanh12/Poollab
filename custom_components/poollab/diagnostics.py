"""Diagnostics for Poollab integration."""

from typing import Any, Dict

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {"email", "password", "token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> Dict[str, Any]:
    """Return diagnostics for a config entry."""

    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    coordinators = data.get("coordinators", {})
    devices = []

    for device_id, device_data in coordinators.items():
        coordinator = device_data.get("coordinator")
        device_info = device_data.get("device", {})
        device_name = device_data.get("name")

        # Build measurement summary from coordinator data
        coordinator_data: dict = getattr(coordinator, "data", None) or {}
        latest_values: dict = coordinator_data.get("latest_values", {})
        measurements: list = coordinator_data.get("measurements", [])
        measurement_summary = {
            param: {
                "value": m.get("value"),
                "unit": m.get("unit"),
                "timestamp": m.get("timestamp"),
            }
            for param, m in latest_values.items()
        }

        # Build API errors report — show all tracked keys even when None so
        # the section is always present and its absence is clearly visible.
        raw_api_errors: dict = getattr(coordinator, "last_api_errors", {})
        api_errors_report = {
            key: (
                {
                    "message": val.get("message"),
                    "type": val.get("type"),
                    "timestamp": val.get("timestamp"),
                }
                if val is not None
                else None
            )
            for key, val in raw_api_errors.items()
        }
        has_active_errors = any(v is not None for v in raw_api_errors.values())

        devices.append(
            {
                "id": device_id,
                "name": device_name,
                "account": device_info.get("account"),
                "serial_number": device_info.get("serialNumber"),
                "coordinator": {
                    "last_update_success": getattr(coordinator, "last_update_success", None),
                    "last_update_success_time": str(
                        getattr(coordinator, "last_update_success_time", None)
                    ),
                    "last_exception": str(getattr(coordinator, "last_exception", None)),
                    "total_measurements_fetched": len(measurements),
                    "latest_measurements": measurement_summary,
                },
                "api_errors": {
                    "has_active_errors": has_active_errors,
                    "errors": api_errors_report,
                },
            }
        )

    return async_redact_data(
        {
            "entry": {
                "title": entry.title,
                "data": async_redact_data(entry.data, TO_REDACT),
                "options": entry.options,
                "unique_id": entry.unique_id,
            },
            "devices": devices,
        },
        TO_REDACT,
    )
