"""Sensor platform for Poollab integration."""

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_OPTION_DEVICES,
    CONF_SANITATION_MODE,
    DOMAIN,
    SANITATION_MODE_CHLORINE,
    SENSOR_CONFIGS,
    SENSOR_TYPE_ACTIVE_OXYGEN,
    SENSOR_TYPE_ALK,
    SENSOR_TYPE_BOUND_CYA,
    SENSOR_TYPE_BROMINE,
    SENSOR_TYPE_CALCIUM_HARDNESS,
    SENSOR_TYPE_CL,
    SENSOR_TYPE_COMBINED_CL,
    SENSOR_TYPE_CYA,
    SENSOR_TYPE_FREE_CL,
    SENSOR_TYPE_INVALID_MEASUREMENT_COUNT,
    SENSOR_TYPE_LAST_MEASUREMENT,
    SENSOR_TYPE_MEASUREMENT_COUNT,
    SENSOR_TYPE_PH,
    SENSOR_TYPE_SALT,
    SENSOR_TYPE_TEMP,
    SENSOR_TYPE_TOTAL_CL,
    SENSOR_TYPE_TOTAL_HARDNESS,
    SENSOR_TYPE_UNBOUND_CL,
    get_sensor_types_for_sanitation,
    is_measurement_value_in_range,
)
from .coordinator import (
    PoollabDataUpdateCoordinator,
    _canonicalize_parameter_name,
)
from .time_utils import parse_measurement_timestamp

_LOGGER = logging.getLogger(__name__)


SENSOR_PARAMETER_NAMES = {
    SENSOR_TYPE_PH: "PL pH",
    SENSOR_TYPE_CL: "PL Chlorine Free",
    SENSOR_TYPE_FREE_CL: "PL Chlorine Free",
    SENSOR_TYPE_TOTAL_CL: "PL Total Chlorine",
    SENSOR_TYPE_BROMINE: "PL Bromine",
    SENSOR_TYPE_ACTIVE_OXYGEN: "PL Active Oxygen",
    SENSOR_TYPE_TEMP: "PL Temperature",
    SENSOR_TYPE_ALK: "PL T-Alka",
    SENSOR_TYPE_CYA: "PL Cyanuric Acid",
    SENSOR_TYPE_SALT: "PL Salt",
    SENSOR_TYPE_CALCIUM_HARDNESS: "PL Calcium Hardness",
    SENSOR_TYPE_TOTAL_HARDNESS: "PL Total Hardness",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = data["coordinators"]
    configured_devices = config_entry.options.get(CONF_OPTION_DEVICES, {})

    sensors = []

    # Create sensors for each device (pool)
    for device_id, device_data in coordinators.items():
        coordinator = device_data["coordinator"]
        device_name = device_data["name"]

        device_mode = device_data.get("sanitation_mode")
        if not device_mode and isinstance(configured_devices.get(device_id), dict):
            device_mode = configured_devices[device_id].get(CONF_SANITATION_MODE)
        if not device_mode:
            device_mode = SANITATION_MODE_CHLORINE

        for sensor_type in get_sensor_types_for_sanitation(device_mode):
            sensors.append(
                PoollabSensor(
                    coordinator,
                    config_entry,
                    device_id,
                    device_name,
                    sensor_type,
                )
            )

    async_add_entities(sensors, False)


class PoollabSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Poollab sensor."""

    def __init__(
        self,
        coordinator: PoollabDataUpdateCoordinator,
        config_entry,
        device_id: str,
        device_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self.device_id = device_id
        self.device_name = device_name
        self._config_entry = config_entry

        # Create unique ID including device
        self._attr_unique_id = f"{config_entry.entry_id}_{device_id}_{sensor_type}"

        config = SENSOR_CONFIGS.get(sensor_type, {})

        # Include device name in sensor name if multiple devices
        sensor_name = config.get("name", sensor_type)
        self._attr_name = f"{self.device_name} {sensor_name}"

        self._attr_icon = config.get("icon", "mdi:water")

        unit = config.get("unit")
        if unit == "°C":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        else:
            self._attr_native_unit_of_measurement = unit

        # Set device class for timestamp sensor
        if sensor_type == SENSOR_TYPE_LAST_MEASUREMENT:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

        # Mark diagnostic sensors
        if sensor_type in (
            SENSOR_TYPE_MEASUREMENT_COUNT,
            SENSOR_TYPE_INVALID_MEASUREMENT_COUNT,
            SENSOR_TYPE_LAST_MEASUREMENT,
        ):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # Set device info to group sensors by pool
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_name,
            "model": "Poollab",
            "manufacturer": "LabCom",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        latest_values = self.coordinator.data.get("latest_values", {})
        active_chlorine = self.coordinator.data.get("active_chlorine", {})

        # Map sensor types to ActiveChlorine keys
        active_chlorine_mapping = {
            SENSOR_TYPE_UNBOUND_CL: "unbound_chlorine",
            SENSOR_TYPE_BOUND_CYA: "bound_to_cya",
        }

        # Handle calculated sensors
        if self.sensor_type == SENSOR_TYPE_COMBINED_CL:
            return self._calculate_combined_chlorine(latest_values)

        # Handle measurement count sensor
        if self.sensor_type == SENSOR_TYPE_MEASUREMENT_COUNT:
            # coordinator.data["measurements"] is already filtered for this device
            measurements = self.coordinator.data.get("measurements", [])
            return len(measurements)

        # Handle invalid measurement count sensor
        if self.sensor_type == SENSOR_TYPE_INVALID_MEASUREMENT_COUNT:
            return self.coordinator.data.get("invalid_measurement_count", 0)

        # Handle last measurement time sensor
        if self.sensor_type == SENSOR_TYPE_LAST_MEASUREMENT:
            raw_ts = self.coordinator.data.get("last_measurement_time")
            return self._parse_timestamp(raw_ts)

        # Handle ActiveChlorine sensors
        if self.sensor_type in active_chlorine_mapping:
            ac_key = active_chlorine_mapping[self.sensor_type]
            if ac_key in active_chlorine:
                value = active_chlorine.get(ac_key)
                if value is not None:
                    try:
                        float_value = float(value)
                        if not is_measurement_value_in_range(self.sensor_type, float_value):
                            config = SENSOR_CONFIGS.get(self.sensor_type, {})
                            _LOGGER.warning(
                                "Value %s for %s is outside valid range [%s, %s], ignoring",
                                float_value,
                                self.sensor_type,
                                config.get("min"),
                                config.get("max"),
                            )
                            return None
                        config = SENSOR_CONFIGS.get(self.sensor_type, {})
                        precision = config.get("precision", 2)
                        if isinstance(precision, int) and precision >= 0:
                            return round(float_value, precision)
                        return float_value
                    except (ValueError, TypeError):
                        return None
            return None

        param_name = SENSOR_PARAMETER_NAMES.get(self.sensor_type)
        if param_name:
            measurement = self._measurement_for_parameter(latest_values, param_name)
            if measurement:
                return self._measurement_native_value(measurement, param_name)

        return None

    @staticmethod
    def _is_numeric_text(value: str) -> bool:
        """Return True if a formatted value can be represented as a number."""
        try:
            float(value)
        except (ValueError, TypeError):
            return False
        return True

    @staticmethod
    def _measurement_for_parameter(latest_values: dict, parameter_name: str):
        """Return a measurement using its canonical parameter name."""
        for raw_name, measurement in latest_values.items():
            if _canonicalize_parameter_name(raw_name) == parameter_name:
                return measurement
        return None

    @staticmethod
    def _measurement_count_for_parameter(measurement_counts: dict, parameter_name: str):
        """Return a count using its canonical parameter name."""
        for raw_name, count in measurement_counts.items():
            if _canonicalize_parameter_name(raw_name) == parameter_name:
                return count
        return None

    def _measurement_native_value(self, measurement: dict, param_name: str):
        """Return a Home Assistant state value for a LabCom measurement."""
        value = measurement.get("value")
        if value is None:
            return None

        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return None

        if not is_measurement_value_in_range(self.sensor_type, float_value):
            config = SENSOR_CONFIGS.get(self.sensor_type, {})
            formatted_value = measurement.get("formatted_value")
            if formatted_value is not None:
                formatted_text = str(formatted_value).strip()
                if formatted_text and not self._is_numeric_text(formatted_text):
                    _LOGGER.warning(
                        "Value %s for parameter %s (%s) is outside valid range [%s, %s], discarding non-numeric formatted status %s",
                        float_value,
                        param_name,
                        self.sensor_type,
                        config.get("min"),
                        config.get("max"),
                        formatted_text,
                    )
                    return None

            _LOGGER.warning(
                "Value %s for parameter %s (%s) is outside valid range [%s, %s], ignoring",
                float_value,
                param_name,
                self.sensor_type,
                config.get("min"),
                config.get("max"),
            )
            return None

        config = SENSOR_CONFIGS.get(self.sensor_type, {})
        precision = config.get("precision", 2)
        if isinstance(precision, int) and precision >= 0:
            return round(float_value, precision)
        return float_value

    @staticmethod
    def _parse_timestamp(raw_ts, assume_timezone=None):
        """Parse a raw timestamp into a timezone-aware datetime."""
        return parse_measurement_timestamp(raw_ts, assume_timezone)

    def _calculate_combined_chlorine(self, latest_values: dict) -> float:
        """Calculate combined chlorine from total and free chlorine, or from active chlorine data.

        Combined Chlorine = Total Chlorine - Free Chlorine

        If Total Chlorine is not directly available, try to use bound_to_cya from ActiveChlorine data.
        """
        free_cl_data = self._measurement_for_parameter(latest_values, "PL Chlorine Free")

        total_cl_data = self._measurement_for_parameter(latest_values, "PL Total Chlorine")

        if free_cl_data and total_cl_data:
            try:
                free_cl = float(free_cl_data.get("value", 0))
                total_cl = float(total_cl_data.get("value", 0))
                combined = total_cl - free_cl
                # Combined chlorine cannot be negative
                return round(max(0.0, combined), 2)
            except (ValueError, TypeError):
                return None

        # Fallback: if total chlorine is not available but we have active chlorine data,
        # we could theoretically use bound_to_cya, but that's not the same as combined chlorine
        # So we return None to indicate data is unavailable
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available (has valid data)."""
        # For combined and total chlorine, check if the required data exists
        if self.sensor_type == SENSOR_TYPE_COMBINED_CL:
            latest_values = self.coordinator.data.get("latest_values", {})
            free_cl_data = self._measurement_for_parameter(latest_values, "PL Chlorine Free")
            total_cl_data = self._measurement_for_parameter(latest_values, "PL Total Chlorine")
            # Only available if we have both free and total chlorine data
            return bool(free_cl_data and total_cl_data and self.native_value is not None)

        if self.sensor_type == SENSOR_TYPE_TOTAL_CL:
            latest_values = self.coordinator.data.get("latest_values", {})
            total_cl_data = self._measurement_for_parameter(latest_values, "PL Total Chlorine")
            # Only available if we have total chlorine data from the API
            return bool(total_cl_data)

        # For other sensors, use the standard coordinator availability
        return self.coordinator.last_update_success and self.native_value is not None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        # Diagnostic sensors have no extra attributes
        if self.sensor_type in (
            SENSOR_TYPE_MEASUREMENT_COUNT,
            SENSOR_TYPE_INVALID_MEASUREMENT_COUNT,
            SENSOR_TYPE_LAST_MEASUREMENT,
        ):
            return {}

        attributes = {}
        latest_values = self.coordinator.data.get("latest_values", {})
        measurement_counts = self.coordinator.data.get("measurement_counts", {})
        measurements = self.coordinator.data.get("measurements", [])

        # Always expose total measurements found for this pool/device.
        attributes["pool_measurement_count"] = len(measurements)

        # Expose missing-source diagnostics for chlorine-related sensors
        if self.sensor_type in [
            SENSOR_TYPE_CL,
            SENSOR_TYPE_FREE_CL,
            SENSOR_TYPE_TOTAL_CL,
            SENSOR_TYPE_COMBINED_CL,
            SENSOR_TYPE_UNBOUND_CL,
            SENSOR_TYPE_BOUND_CYA,
        ]:
            missing_parameters = []

            if (
                self.sensor_type
                in [SENSOR_TYPE_CL, SENSOR_TYPE_FREE_CL, SENSOR_TYPE_UNBOUND_CL, SENSOR_TYPE_BOUND_CYA]
                and not self._measurement_for_parameter(latest_values, "PL Chlorine Free")
            ):
                missing_parameters.append("PL Chlorine Free")

            if (
                self.sensor_type in [SENSOR_TYPE_TOTAL_CL, SENSOR_TYPE_COMBINED_CL]
                and not self._measurement_for_parameter(latest_values, "PL Total Chlorine")
            ):
                missing_parameters.append("PL Total Chlorine/PL Chlorine Total")

            if (
                self.sensor_type in [SENSOR_TYPE_UNBOUND_CL, SENSOR_TYPE_BOUND_CYA]
                and not self._measurement_for_parameter(latest_values, "PL pH")
            ):
                missing_parameters.append("PL pH")

            if missing_parameters:
                attributes["missing_parameters"] = missing_parameters
                attributes["diagnostic"] = "Missing required measurements for this sensor"

        # Add chlorine chemistry info for chlorine sensors
        if self.sensor_type in [SENSOR_TYPE_FREE_CL, SENSOR_TYPE_TOTAL_CL, SENSOR_TYPE_COMBINED_CL]:

            if self.sensor_type == SENSOR_TYPE_FREE_CL:
                attributes["description"] = "Active chlorine available for sanitization"
                attributes["ideal_range"] = "1-3 ppm"
                attributes["also_known_as"] = "Active Chlorine"
                # Add measurement timestamp if available
                free_cl_data = self._measurement_for_parameter(latest_values, "PL Chlorine Free")
                if free_cl_data:
                    attributes["timestamp"] = free_cl_data.get("timestamp")

            elif self.sensor_type == SENSOR_TYPE_TOTAL_CL:
                attributes["description"] = "Total chlorine (free + combined)"
                attributes["calculation"] = "Total = Free + Combined"
                # Add measurement timestamp if available
                total_cl_data = self._measurement_for_parameter(latest_values, "PL Total Chlorine")
                if total_cl_data:
                    attributes["timestamp"] = total_cl_data.get("timestamp")
                else:
                    attributes["note"] = "Total chlorine not directly measured by Poollab device. This value would come from lab testing."

            elif self.sensor_type == SENSOR_TYPE_COMBINED_CL:
                attributes["description"] = "Chlorine bound to contaminants (chloramines)"
                attributes["calculation"] = "Combined = Total - Free"
                attributes["ideal_range"] = "< 0.5 ppm"
                attributes["warning"] = "High combined chlorine indicates poor water quality"

                # Add source values for calculated sensor
                free_cl_data = self._measurement_for_parameter(latest_values, "PL Chlorine Free")
                total_cl_data = self._measurement_for_parameter(latest_values, "PL Total Chlorine")
                if free_cl_data:
                    attributes["free_chlorine"] = free_cl_data.get("value")
                    attributes["free_chlorine_timestamp"] = free_cl_data.get("timestamp")
                if total_cl_data:
                    attributes["total_chlorine"] = total_cl_data.get("value")
                    attributes["total_chlorine_timestamp"] = total_cl_data.get("timestamp")
                else:
                    attributes["note"] = "Combined chlorine cannot be calculated without total chlorine measurement. Please add total chlorine via manual input or testing."

        if self.sensor_type == SENSOR_TYPE_BROMINE:
            attributes["description"] = "Bromine residual for sanitization"
            attributes["ideal_range"] = "3-5 ppm for spas; follow product guidance"

        if self.sensor_type == SENSOR_TYPE_ACTIVE_OXYGEN:
            attributes["description"] = "Active oxygen residual"
            attributes["also_known_as"] = "MPS"

        # Add timestamp for any sensor
        param_name = SENSOR_PARAMETER_NAMES.get(self.sensor_type)
        if param_name:
            measurement = self._measurement_for_parameter(latest_values, param_name)
            if measurement:
                if measurement.get("value") is not None:
                    attributes["raw_value"] = measurement.get("value")
                if measurement.get("unit"):
                    attributes["api_unit"] = measurement.get("unit")
                if measurement.get("formatted_value") is not None:
                    attributes["formatted_value"] = measurement.get("formatted_value")
                if measurement.get("ideal_low") is not None:
                    attributes["ideal_low"] = measurement.get("ideal_low")
                if measurement.get("ideal_high") is not None:
                    attributes["ideal_high"] = measurement.get("ideal_high")
                if measurement.get("ideal_status"):
                    attributes["ideal_status"] = measurement.get("ideal_status")
                if "timestamp" not in attributes and measurement.get("timestamp"):
                    attributes["timestamp"] = measurement.get("timestamp")
                measurement_count = self._measurement_count_for_parameter(
                    measurement_counts,
                    param_name,
                )
                if measurement_count is not None:
                    attributes["measurement_count"] = measurement_count

        # Combined chlorine is calculated from free and total chlorine sources.
        if self.sensor_type == SENSOR_TYPE_COMBINED_CL:
            free_count = self._measurement_count_for_parameter(
                measurement_counts,
                "PL Chlorine Free",
            )
            total_count = self._measurement_count_for_parameter(
                measurement_counts,
                "PL Total Chlorine",
            )
            if free_count is not None:
                attributes["free_chlorine_measurement_count"] = free_count
            if total_count is not None:
                attributes["total_chlorine_measurement_count"] = total_count

        # Add info for ActiveChlorine calculated sensors
        if self.sensor_type in [SENSOR_TYPE_UNBOUND_CL, SENSOR_TYPE_BOUND_CYA]:
            active_chlorine = self.coordinator.data.get("active_chlorine", {})

            if self.sensor_type == SENSOR_TYPE_UNBOUND_CL:
                attributes["description"] = "Free chlorine available for sanitization"
                attributes["ideal_range"] = "1-3 ppm"
                attributes["also_known_as"] = "HOCl + OCl-"

            elif self.sensor_type == SENSOR_TYPE_BOUND_CYA:
                attributes["description"] = "Chlorine bound to stabilizer (CYA)"
                attributes["calculation"] = "Chlorine speciation with respect to CYA"

            # Add all ActiveChlorine values as attributes for reference
            if active_chlorine:
                for key, value in active_chlorine.items():
                    attributes[f"ac_{key}"] = value

        return attributes
