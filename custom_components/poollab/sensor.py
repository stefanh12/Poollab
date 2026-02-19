"""Sensor platform for Poollab integration."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
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

        # Map sensor types to Labcom parameter names
        sensor_mapping = {
            SENSOR_TYPE_PH: "PL pH",
            SENSOR_TYPE_CL: "PL Chlorine Free",
            SENSOR_TYPE_FREE_CL: "PL Chlorine Free",
            SENSOR_TYPE_TOTAL_CL: "PL Total Chlorine",
            SENSOR_TYPE_TEMP: "PL Temperature",
            SENSOR_TYPE_ALK: "PL T-Alka",
            SENSOR_TYPE_CYA: "PL Cyanuric Acid",
            SENSOR_TYPE_SALT: "PL Salt",
        }

        # Handle calculated sensors
        if self.sensor_type == SENSOR_TYPE_COMBINED_CL:
            return self._calculate_combined_chlorine(latest_values)

        param_name = sensor_mapping.get(self.sensor_type)
        if param_name and param_name in latest_values:
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
        """Calculate combined chlorine from total and free chlorine."""
        free_cl_data = latest_values.get("PL Chlorine Free")
        total_cl_data = latest_values.get("PL Total Chlorine")

        if free_cl_data and total_cl_data:
            try:
                free_cl = float(free_cl_data.get("value", 0))
                total_cl = float(total_cl_data.get("value", 0))
                combined = total_cl - free_cl
                # Combined chlorine cannot be negative
                return round(max(0.0, combined), 2)
            except (ValueError, TypeError):
                return None

        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        if not self.coordinator.data:
            return {}

        attributes = {}
        latest_values = self.coordinator.data.get("latest_values", {})

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
                total_cl_data = latest_values.get("PL Total Chlorine")
                if total_cl_data:
                    attributes["timestamp"] = total_cl_data.get("timestamp")

            elif self.sensor_type == SENSOR_TYPE_COMBINED_CL:
                attributes["description"] = "Chlorine bound to contaminants (chloramines)"
                attributes["calculation"] = "Combined = Total - Free"
                attributes["ideal_range"] = "< 0.5 ppm"
                attributes["warning"] = "High combined chlorine indicates poor water quality"

                # Add source values for calculated sensor
                free_cl_data = latest_values.get("PL Chlorine Free")
                total_cl_data = latest_values.get("PL Total Chlorine")
                if free_cl_data:
                    attributes["free_chlorine"] = free_cl_data.get("value")
                    attributes["free_chlorine_timestamp"] = free_cl_data.get("timestamp")
                if total_cl_data:
                    attributes["total_chlorine"] = total_cl_data.get("value")
                    attributes["total_chlorine_timestamp"] = total_cl_data.get("timestamp")

        # Add timestamp for any sensor
        sensor_mapping = {
            SENSOR_TYPE_PH: "PL pH",
            SENSOR_TYPE_CL: "PL Chlorine Free",
            SENSOR_TYPE_TEMP: "PL Temperature",
            SENSOR_TYPE_ALK: "PL T-Alka",
            SENSOR_TYPE_CYA: "PL Cyanuric Acid",
            SENSOR_TYPE_SALT: "PL Salt",
        }

        param_name = sensor_mapping.get(self.sensor_type)
        if param_name and param_name in latest_values:
            measurement = latest_values[param_name]
            if "timestamp" not in attributes and measurement.get("timestamp"):
                attributes["timestamp"] = measurement.get("timestamp")

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
