"""Services for Poollab integration."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType

SERVICE_REFRESH_DATA = "refresh_data"


async def async_setup_services(hass: HomeAssistant, config_entry) -> None:
    """Set up services for Poollab."""

    async def handle_refresh_data(call):
        """Handle refresh data service call."""
        from .const import DOMAIN
        
        coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DATA,
        handle_refresh_data,
    )
