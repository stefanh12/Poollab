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
            _LOGGER.debug("Starting data update for device: %s", self.device_id)
            
            try:
                measurements = await asyncio.wait_for(
                    self.api_client.get_measurements(),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                _LOGGER.error("Timeout fetching measurements for device %s", self.device_id)
                raise UpdateFailed(f"Timeout fetching measurements for device {self.device_id}")

            if measurements is None:
                _LOGGER.warning("API returned None for measurements")
                measurements = []
            
            if not measurements:
                _LOGGER.warning("No measurements available from Poollab API for device %s", self.device_id)
                # Don't fail, just return empty data so coordinator doesn't error
                return {
                    "device_id": self.device_id,
                    "measurements": [],
                    "latest_values": {},
                }

            _LOGGER.debug(
                "Total measurements received: %d, filtering for device: %s",
                len(measurements),
                self.device_id,
            )

            # Filter measurements for this device account
            device_measurements = [
                m for m in measurements
                if m.get("account") == self.device_id or m.get("device_serial") == self.device_id
            ]

            _LOGGER.info(
                "Found %d measurements for device %s",
                len(device_measurements),
                self.device_id,
            )

            if not device_measurements:
                _LOGGER.warning(f"No measurements found for device {self.device_id}")
                device_measurements = []

            # Extract latest values for each parameter
            latest_values = {}
            for measurement in device_measurements:
                param = measurement.get("parameter", "unknown")
                latest_values[param] = measurement
                _LOGGER.debug(
                    "Device %s - Parameter: %s, Value: %s, Timestamp: %s",
                    self.device_id,
                    param,
                    measurement.get("value"),
                    measurement.get("timestamp"),
                )

            _LOGGER.info(
                "Device %s has %d unique parameters with latest values",
                self.device_id,
                len(latest_values),
            )

            return {
                "device_id": self.device_id,
                "measurements": device_measurements,
                "latest_values": latest_values,
            }
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to Poollab API: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Error updating data for device %s: %s", self.device_id, err, exc_info=True)
            raise UpdateFailed(f"Error communicating with Poollab API: {err}") from err
