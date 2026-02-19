"""Data update coordinator for Poollab integration."""

import asyncio
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import PoollabApiClient
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PoollabDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Poollab data from API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: PoollabApiClient,
        device_id: str,
    ):
        """Initialize the data update coordinator."""
        self.api_client = api_client
        self.device_id = device_id
        self.data = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from Poollab API."""
        try:
            device_info = await self.api_client.get_device_info(self.device_id)
            readings = await self.api_client.get_device_readings(self.device_id)
            
            if not readings:
                raise UpdateFailed("No readings available from Poollab API")

            return {
                "device_info": device_info,
                "readings": readings,
            }
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to Poollab API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Poollab API: {err}") from err
