"""Sensor platform for Poollab integration."""

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PoollabDataUpdateCoordinator
from .const import (
    DOMAIN,
    SENSOR_CONFIGS,
    SENSOR_TYPE_PH,
    SENSOR_TYPE_CL,
    SENSOR_TYPE_FREE_CL,
    SENSOR_TYPE_TOTAL_CL,
    SENSOR_TYPE_COMBINED_CL,
    SENSOR_TYPE_TEMP,
    SENSOR_TYPE_ALK,
    SENSOR_TYPE_CYA,
    SENSOR_TYPE_SALT,
    SENSOR_TYPE_UNBOUND_CL,
    SENSOR_TYPE_BOUND_CYA,
    SENSOR_TYPE_MEASUREMENT_COUNT,
    SENSOR_TYPE_LAST_MEASUREMENT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinators = data["coordinators"]

    sensors = []

    # Create sensors for each device (pool)
    for device_id, device_data in coordinators.items():
        coordinator = device_data["coordinator"]
        device_name = device_data["name"]

        for sensor_type in [
            SENSOR_TYPE_PH,
            SENSOR_TYPE_CL,
            SENSOR_TYPE_FREE_CL,
            SENSOR_TYPE_TOTAL_CL,
            SENSOR_TYPE_COMBINED_CL,
            SENSOR_TYPE_TEMP,
            SENSOR_TYPE_ALK,
            SENSOR_TYPE_CYA,
            SENSOR_TYPE_SALT,
            SENSOR_TYPE_UNBOUND_CL,
            SENSOR_TYPE_BOUND_CYA,
            SENSOR_TYPE_MEASUREMENT_COUNT,
            SENSOR_TYPE_LAST_MEASUREMENT,
        ]:
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

        # Map sensor types to Labcom parameter names with alternate names as fallback
        sensor_mapping = {
            SENSOR_TYPE_PH: ("PL pH",),
            SENSOR_TYPE_CL: ("PL Chlorine Free",),
            SENSOR_TYPE_FREE_CL: ("PL Chlorine Free",),
            SENSOR_TYPE_TOTAL_CL: ("PL Total Chlorine", "PL Chlorine Total"),
            SENSOR_TYPE_TEMP: ("PL Temperature",),
            SENSOR_TYPE_ALK: ("PL T-Alka",),
            SENSOR_TYPE_CYA: ("PL Cyanuric Acid",),
            SENSOR_TYPE_SALT: ("PL Salt",),
        }

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
            measurements = self.coordinator.data.get("measurements", [])
            return len(measurements)

        # Handle last measurement time sensor
        if self.sensor_type == SENSOR_TYPE_LAST_MEASUREMENT:
            raw_ts = self.coordinator.data.get("last_measurement_time")
            if raw_ts is None:
                return None
            try:
                if isinstance(raw_ts, (int, float)):
                    ts = float(raw_ts)
                    ts = ts / 1000.0 if ts > 1e12 else ts
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                ts_str = str(raw_ts).strip()
                if ts_str.isdigit():
                    ts = float(ts_str)
                    ts = ts / 1000.0 if ts > 1e12 else ts
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, TypeError, OSError):
                return None

        # Handle ActiveChlorine sensors
        if self.sensor_type in active_chlorine_mapping:
            ac_key = active_chlorine_mapping[self.sensor_type]
            if ac_key in active_chlorine:
                value = active_chlorine.get(ac_key)
                if value is not None:
                    try:
                        config = SENSOR_CONFIGS.get(self.sensor_type, {})
                        precision = config.get("precision", 2)
                        if isinstance(precision, int) and precision >= 0:
                            return round(float(value), precision)
                        return float(value)
                    except (ValueError, TypeError):
                        return None
            return None

        # Try primary and alternate parameter names
        param_names = sensor_mapping.get(self.sensor_type)
        if param_names:
            for param_name in param_names:
                if param_name in latest_values:
                    measurement = latest_values[param_name]
                    value = measurement.get("value")
                    if value is not None:
                        try:
                            config = SENSOR_CONFIGS.get(self.sensor_type, {})
                            precision = config.get("precision", 2)
                            if isinstance(precision, int) and precision >= 0:
                                return round(float(value), precision)
                            return float(value)
                        except (ValueError, TypeError):
                            return None

        return None

    def _calculate_combined_chlorine(self, latest_values: dict) -> float:
        """Calculate combined chlorine from total and free chlorine, or from active chlorine data.
        
        Combined Chlorine = Total Chlorine - Free Chlorine
        
        If Total Chlorine is not directly available, try to use bound_to_cya from ActiveChlorine data.
        """
        free_cl_data = latest_values.get("PL Chlorine Free")
        
        # Try primary and alternate names for total chlorine
        total_cl_data = latest_values.get("PL Total Chlorine") or latest_values.get("PL Chlorine Total")

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
            free_cl_data = latest_values.get("PL Chlorine Free")
            total_cl_data = latest_values.get("PL Total Chlorine") or latest_values.get("PL Chlorine Total")
            # Only available if we have both free and total chlorine data
            return bool(free_cl_data and total_cl_data and self.native_value is not None)
        
        if self.sensor_type == SENSOR_TYPE_TOTAL_CL:
            latest_values = self.coordinator.data.get("latest_values", {})
            total_cl_data = latest_values.get("PL Total Chlorine") or latest_values.get("PL Chlorine Total")
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
        if self.sensor_type in (SENSOR_TYPE_MEASUREMENT_COUNT, SENSOR_TYPE_LAST_MEASUREMENT):
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

            if self.sensor_type in [SENSOR_TYPE_CL, SENSOR_TYPE_FREE_CL, SENSOR_TYPE_UNBOUND_CL, SENSOR_TYPE_BOUND_CYA]:
                if "PL Chlorine Free" not in latest_values:
                    missing_parameters.append("PL Chlorine Free")

            if self.sensor_type in [SENSOR_TYPE_TOTAL_CL, SENSOR_TYPE_COMBINED_CL]:
                if (
                    "PL Total Chlorine" not in latest_values
                    and "PL Chlorine Total" not in latest_values
                ):
                    missing_parameters.append("PL Total Chlorine/PL Chlorine Total")

            if self.sensor_type in [SENSOR_TYPE_UNBOUND_CL, SENSOR_TYPE_BOUND_CYA]:
                if "PL pH" not in latest_values:
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
                free_cl_data = latest_values.get("PL Chlorine Free")
                if free_cl_data:
                    attributes["timestamp"] = free_cl_data.get("timestamp")

            elif self.sensor_type == SENSOR_TYPE_TOTAL_CL:
                attributes["description"] = "Total chlorine (free + combined)"
                attributes["calculation"] = "Total = Free + Combined"
                # Add measurement timestamp if available
                total_cl_data = latest_values.get("PL Total Chlorine") or latest_values.get("PL Chlorine Total")
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
                free_cl_data = latest_values.get("PL Chlorine Free")
                total_cl_data = latest_values.get("PL Total Chlorine") or latest_values.get("PL Chlorine Total")
                if free_cl_data:
                    attributes["free_chlorine"] = free_cl_data.get("value")
                    attributes["free_chlorine_timestamp"] = free_cl_data.get("timestamp")
                if total_cl_data:
                    attributes["total_chlorine"] = total_cl_data.get("value")
                    attributes["total_chlorine_timestamp"] = total_cl_data.get("timestamp")
                else:
                    attributes["note"] = "Combined chlorine cannot be calculated without total chlorine measurement. Please add total chlorine via manual input or testing."

        # Add timestamp for any sensor
        sensor_mapping = {
            SENSOR_TYPE_PH: ("PL pH",),
            SENSOR_TYPE_CL: ("PL Chlorine Free",),
            SENSOR_TYPE_FREE_CL: ("PL Chlorine Free",),
            SENSOR_TYPE_TOTAL_CL: ("PL Total Chlorine", "PL Chlorine Total"),
            SENSOR_TYPE_TEMP: ("PL Temperature",),
            SENSOR_TYPE_ALK: ("PL T-Alka",),
            SENSOR_TYPE_CYA: ("PL Cyanuric Acid",),
            SENSOR_TYPE_SALT: ("PL Salt",),
        }

        param_names = sensor_mapping.get(self.sensor_type)
        if param_names:
            for param_name in param_names:
                if param_name in latest_values:
                    measurement = latest_values[param_name]
                    # Add timestamp if not already present
                    if "timestamp" not in attributes and measurement.get("timestamp"):
                        attributes["timestamp"] = measurement.get("timestamp")
                    # Add measurement count
                    if param_name in measurement_counts:
                        attributes["measurement_count"] = measurement_counts[param_name]
                    break

        # Combined chlorine is calculated from free and total chlorine sources.
        if self.sensor_type == SENSOR_TYPE_COMBINED_CL:
            free_count = measurement_counts.get("PL Chlorine Free")
            total_count = measurement_counts.get("PL Total Chlorine") or measurement_counts.get("PL Chlorine Total")
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
