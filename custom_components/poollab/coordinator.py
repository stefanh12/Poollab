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
            measurements = await self.api_client.get_measurements()

            if not measurements:
                raise UpdateFailed("No measurements available from Poollab API")

            # Filter measurements for this device account
            device_measurements = [
                m for m in measurements
                if m.get("account") == self.device_id or m.get("device_serial") == self.device_id
            ]

            if not device_measurements:
                _LOGGER.warning(f"No measurements found for device {self.device_id}")
                device_measurements = []

            # Extract latest values for each parameter
            latest_values = {}
            for measurement in device_measurements:
                param = measurement.get("parameter", "unknown")
                latest_values[param] = measurement

            return {
                "device_id": self.device_id,
                "measurements": device_measurements,
                "latest_values": latest_values,
            }
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to Poollab API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Poollab API: {err}") from err
