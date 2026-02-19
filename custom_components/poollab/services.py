"""Services for Poollab integration."""

from homeassistant.core import HomeAssistant

from .const import DOMAIN

SERVICE_REFRESH_DATA = "refresh_data"


async def async_setup_services(hass: HomeAssistant, config_entry) -> None:
    """Set up services for Poollab."""

    async def handle_refresh_data(_call):
        """Handle refresh data service call."""
        coordinators = hass.data[DOMAIN][config_entry.entry_id]["coordinators"]
        for device_data in coordinators.values():
            await device_data["coordinator"].async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DATA,
        handle_refresh_data,
    )
