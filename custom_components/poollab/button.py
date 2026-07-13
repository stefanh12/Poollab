"""Button platform for Poollab integration."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UPDATE_MODE_MANUAL
from .coordinator import PoollabDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Poollab buttons."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = data["coordinators"]

    buttons = []
    for device_id, device_data in coordinators.items():
        if device_data.get("update_mode") != UPDATE_MODE_MANUAL:
            continue

        buttons.append(
            PoollabRefreshButton(
                device_data["coordinator"],
                config_entry,
                device_id,
                device_data["name"],
            )
        )

    async_add_entities(buttons, False)


class PoollabRefreshButton(CoordinatorEntity, ButtonEntity):
    """Button entity for manual Poollab data refresh."""

    def __init__(
        self,
        coordinator: PoollabDataUpdateCoordinator,
        config_entry,
        device_id: str,
        device_name: str,
    ) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{config_entry.entry_id}_{device_id}_refresh"
        self._attr_name = f"{device_name} Refresh Data"
        self._attr_icon = "mdi:refresh"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_name,
            "model": "Poollab",
            "manufacturer": "LabCom",
        }

    async def async_press(self) -> None:
        """Refresh backend data on demand."""
        await self.coordinator.async_request_refresh()
