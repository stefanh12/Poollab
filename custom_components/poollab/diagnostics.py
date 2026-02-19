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
    
    coordinator = data.get("coordinator")
    device_id = data.get("device_id")
    
    return async_redact_data(
        {
            "entry": {
                "title": entry.title,
                "data": async_redact_data(entry.data, TO_REDACT),
                "options": entry.options,
                "unique_id": entry.unique_id,
            },
            "coordinator": {
                "last_update_success": coordinator.last_update_success if coordinator else None,
                "last_update_time": str(coordinator.last_update) if coordinator else None,
                "data_available": bool(coordinator.data) if coordinator else False,
            },
            "device": {
                "id": device_id,
            },
        },
        TO_REDACT,
    )
