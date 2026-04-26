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
                    "data_available": bool(getattr(coordinator, "data", None)),
                },
                "api_errors": getattr(coordinator, "last_api_errors", {}),
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
