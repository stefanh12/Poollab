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

        device_data = self.coordinator.data.get("device", {})
        last_reading = device_data.get("lastReading", {})
        
        # Handle calculated sensors
        if self.sensor_type == SENSOR_TYPE_COMBINED_CL:
            return self._calculate_combined_chlorine(last_reading)
        
        sensor_mapping = {
            SENSOR_TYPE_PH: "ph",
            SENSOR_TYPE_CL: "chlorine",
            SENSOR_TYPE_FREE_CL: "freeChlorine",
            SENSOR_TYPE_TOTAL_CL: "totalChlorine",
            SENSOR_TYPE_TEMP: "temperature",
            SENSOR_TYPE_ALK: "alkalinity",
            SENSOR_TYPE_CYA: "cya",
            SENSOR_TYPE_SALT: "salt",
        }

        sensor_key = sensor_mapping.get(self.sensor_type)
        if sensor_key:
            value = last_reading.get(sensor_key)
            if value is not None:
                config = SENSOR_CONFIGS.get(self.sensor_type, {})
                precision = config.get("precision", 2)
                if isinstance(precision, int) and precision >= 0:
                    return round(float(value), precision)
                return value

        return None

    def _calculate_combined_chlorine(self, last_reading: dict) -> float:
        """Calculate combined chlorine from total and free chlorine."""
        total_cl = last_reading.get("totalChlorine")
        free_cl = last_reading.get("freeChlorine")
        
        if total_cl is not None and free_cl is not None:
            try:
                combined = float(total_cl) - float(free_cl)
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
        
        # Add chlorine chemistry info for chlorine sensors
        if self.sensor_type in [SENSOR_TYPE_FREE_CL, SENSOR_TYPE_TOTAL_CL, SENSOR_TYPE_COMBINED_CL]:
            last_reading = self.coordinator.data.get("device", {}).get("lastReading", {})
            
            if self.sensor_type == SENSOR_TYPE_FREE_CL:
                attributes["description"] = "Active chlorine available for sanitization"
                attributes["ideal_range"] = "1-3 ppm"
                attributes["also_known_as"] = "Active Chlorine"
            
            elif self.sensor_type == SENSOR_TYPE_TOTAL_CL:
                attributes["description"] = "Total chlorine (free + combined)"
                attributes["calculation"] = "Total = Free + Combined"
            
            elif self.sensor_type == SENSOR_TYPE_COMBINED_CL:
                attributes["description"] = "Chlorine bound to contaminants (chloramines)"
                attributes["calculation"] = "Combined = Total - Free"
                attributes["ideal_range"] = "< 0.5 ppm"
                attributes["warning"] = "High combined chlorine indicates poor water quality"
                
                # Add source values for calculated sensor
                free_cl = last_reading.get("freeChlorine")
                total_cl = last_reading.get("totalChlorine")
                if free_cl is not None:
                    attributes["free_chlorine"] = free_cl
                if total_cl is not None:
                    attributes["total_chlorine"] = total_cl
        
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
