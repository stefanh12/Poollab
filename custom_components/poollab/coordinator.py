"""Data update coordinator for Poollab integration."""

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import PoollabApiClient
from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    SENSOR_CONFIGS,
    SENSOR_TYPE_PH,
    SENSOR_TYPE_FREE_CL,
    SENSOR_TYPE_CYA,
    SENSOR_TYPE_TEMP,
    is_measurement_value_in_range,
)

_LOGGER = logging.getLogger(__name__)


def _timestamp_sort_key(measurement: dict) -> float:
    """Return a sortable timestamp key supporting unix and ISO formats."""
    raw_ts = measurement.get("timestamp")
    if raw_ts is None:
        return 0.0

    # Numeric unix timestamp (seconds or milliseconds)
    if isinstance(raw_ts, (int, float)):
        ts = float(raw_ts)
        return ts / 1000.0 if ts > 1e12 else ts

    # Numeric string unix timestamp
    if isinstance(raw_ts, str):
        ts_str = raw_ts.strip()
        if ts_str.isdigit():
            ts = float(ts_str)
            return ts / 1000.0 if ts > 1e12 else ts

        # ISO string, commonly ending with Z
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            return 0.0

    return 0.0


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
        self._last_api_errors: dict[str, dict | None] = {
            "measurements": None,
            "active_chlorine": None,
            "update": None,
        }

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    @property
    def last_api_errors(self) -> dict[str, dict | None]:
        """Return the latest API-related errors for diagnostics."""
        return self._last_api_errors

    def _set_api_error(
        self,
        error_key: str,
        message: str,
        error_type: str,
    ) -> None:
        """Store an API error for later diagnostics."""
        self._last_api_errors[error_key] = {
            "message": message,
            "type": error_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "device_id": self.device_id,
        }

    def _clear_api_error(self, error_key: str) -> None:
        """Clear a stored API error when call path succeeds again."""
        self._last_api_errors[error_key] = None

    async def _async_update_data(self) -> dict:
        """Fetch data from Poollab API."""
        try:
            _LOGGER.debug("Starting data update for device: %s", self.device_id)

            try:
                measurements = await asyncio.wait_for(
                    self.api_client.get_measurements(),
                    timeout=30.0
                )
                self._clear_api_error("measurements")
            except asyncio.TimeoutError:
                _LOGGER.error("Timeout fetching measurements for device %s", self.device_id)
                self._set_api_error(
                    "measurements",
                    "Timeout while fetching measurements from backend",
                    "timeout",
                )
                self._set_api_error(
                    "update",
                    "Update failed due to measurements timeout",
                    "update_failed",
                )
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
                    "active_chlorine": {},
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
            # Group measurements by parameter, then take the last one (most recent)
            params_by_param = {}
            for measurement in device_measurements:
                param = measurement.get("parameter", "unknown")
                if param not in params_by_param:
                    params_by_param[param] = []
                params_by_param[param].append(measurement)

            latest_values = {}
            for param, param_list in params_by_param.items():
                # Sort by timestamp (descending) to ensure we get the truly latest measurement
                # API may return measurements in any order, so we must sort to be safe
                try:
                    sorted_list = sorted(
                        param_list,
                        key=_timestamp_sort_key,
                        reverse=True
                    )
                    latest_measurement = sorted_list[0]
                except (ValueError, IndexError, TypeError) as e:
                    _LOGGER.warning(
                        "Error sorting measurements for parameter %s: %s, using first available",
                        param,
                        e,
                    )
                    latest_measurement = param_list[0]

                latest_values[param] = latest_measurement
                _LOGGER.debug(
                    "Device %s - Parameter: %s, Total measurements: %d, Latest ID: %d, Latest value: %s (%s), Latest timestamp: %s",
                    self.device_id,
                    param,
                    len(param_list),
                    latest_measurement.get("id"),
                    latest_measurement.get("value"),
                    latest_measurement.get("unit"),
                    latest_measurement.get("timestamp"),
                )

            _LOGGER.info(
                "Device %s has %d unique parameters with latest values",
                self.device_id,
                len(latest_values),
            )

            # Prepare ActiveChlorine calculation data (optional, non-blocking)
            active_chlorine_data = {}
            try:
                # Extract required values for ActiveChlorine calculation
                ph_data = latest_values.get("PL pH")
                chlorine_data = latest_values.get("PL Chlorine Free")
                cya_data = latest_values.get("PL Cyanuric Acid")
                temp_data = latest_values.get("PL Temperature")

                # Check if we have the minimum required parameters
                if ph_data and chlorine_data:
                    ph = float(ph_data.get("value", 7.0))
                    chlorine = float(chlorine_data.get("value", 0.0))
                    cya = float(cya_data.get("value", 0.0)) if cya_data else 0.0
                    temperature = float(temp_data.get("value", 25.0)) if temp_data else 25.0

                    # Validate inputs are within reasonable ranges before calling the API
                    invalid_inputs = []
                    for sensor_type, param_name, value in [
                        (SENSOR_TYPE_PH, "pH", ph),
                        (SENSOR_TYPE_FREE_CL, "chlorine", chlorine),
                        (SENSOR_TYPE_CYA, "cya", cya),
                        (SENSOR_TYPE_TEMP, "temperature", temperature),
                    ]:
                        if not is_measurement_value_in_range(sensor_type, value):
                            cfg = SENSOR_CONFIGS.get(sensor_type, {})
                            _LOGGER.warning(
                                "ActiveChlorine input %s=%s is outside valid range [%s, %s] for device %s, skipping calculation",
                                param_name,
                                value,
                                cfg.get("min"),
                                cfg.get("max"),
                                self.device_id,
                            )
                            invalid_inputs.append(param_name)

                    if invalid_inputs:
                        _LOGGER.debug(
                            "Skipping ActiveChlorine calculation for device %s due to out-of-range inputs: %s",
                            self.device_id,
                            invalid_inputs,
                        )
                    else:
                        _LOGGER.debug(
                            "Calling ActiveChlorine API for device %s with temp=%s, pH=%s, chlorine=%s, cya=%s",
                            self.device_id,
                            temperature,
                            ph,
                            chlorine,
                            cya,
                        )

                        try:
                            active_chlorine_result = await asyncio.wait_for(
                                self.api_client.get_active_chlorine(temperature, ph, chlorine, cya),
                                timeout=20.0
                            )

                            if active_chlorine_result:
                                active_chlorine_data = active_chlorine_result
                                self._clear_api_error("active_chlorine")
                                _LOGGER.info(
                                    "Device %s - ActiveChlorine calculated: unbound_chlorine=%s, bound_to_cya=%s",
                                    self.device_id,
                                    active_chlorine_data.get("unbound_chlorine"),
                                    active_chlorine_data.get("bound_to_cya"),
                                )
                            else:
                                _LOGGER.warning("Failed to calculate ActiveChlorine for device %s", self.device_id)
                                self._set_api_error(
                                    "active_chlorine",
                                    "ActiveChlorine backend returned no data",
                                    "empty_response",
                                )
                        except asyncio.TimeoutError:
                            _LOGGER.warning(
                                "Timeout calculating ActiveChlorine for device %s, continuing without it",
                                self.device_id,
                            )
                            self._set_api_error(
                                "active_chlorine",
                                "Timeout while calculating ActiveChlorine",
                                "timeout",
                            )
                        except Exception as e:
                            _LOGGER.warning(
                                "Error calculating ActiveChlorine for device %s: %s, continuing without it",
                                self.device_id,
                                e,
                            )
                            self._set_api_error(
                                "active_chlorine",
                                str(e),
                                "exception",
                            )
                else:
                    _LOGGER.debug(
                        "Insufficient data for ActiveChlorine calculation for device %s (pH: %s, Chlorine: %s)",
                        self.device_id,
                        "present" if ph_data else "missing",
                        "present" if chlorine_data else "missing",
                    )
            except Exception as e:
                _LOGGER.warning(
                    "Unexpected error preparing ActiveChlorine for device %s: %s",
                    self.device_id,
                    e,
                )

            # Build measurement counts for each parameter
            measurement_counts = {param: len(param_list) for param, param_list in params_by_param.items()}

            # Find the most recent measurement timestamp across all parameters
            last_measurement_time: Optional[str] = None
            if device_measurements:
                try:
                    most_recent = max(device_measurements, key=_timestamp_sort_key)
                    last_measurement_time = most_recent.get("timestamp")
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Error finding last measurement time for device %s: %s", self.device_id, e)

            return {
                "device_id": self.device_id,
                "measurements": device_measurements,
                "latest_values": latest_values,
                "measurement_counts": measurement_counts,
                "active_chlorine": active_chlorine_data,
                "last_measurement_time": last_measurement_time,
            }
        except asyncio.TimeoutError as err:
            self._set_api_error(
                "update",
                f"Timeout connecting to Poollab API: {err}",
                "timeout",
            )
            raise UpdateFailed(f"Timeout connecting to Poollab API: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Error updating data for device %s: %s", self.device_id, err, exc_info=True)
            self._set_api_error(
                "update",
                str(err),
                "exception",
            )
            raise UpdateFailed(f"Error communicating with Poollab API: {err}") from err
