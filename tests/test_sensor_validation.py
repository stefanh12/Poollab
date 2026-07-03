"""Tests for sensor value range validation."""

import importlib
import sys
from types import ModuleType, SimpleNamespace

from poollab.const import (
    is_measurement_value_in_range,
    SENSOR_TYPE_PH,
    SENSOR_TYPE_FREE_CL,
    SENSOR_TYPE_BROMINE,
    SENSOR_TYPE_ACTIVE_OXYGEN,
    SENSOR_TYPE_TEMP,
    SENSOR_TYPE_ALK,
    SENSOR_TYPE_CYA,
    SENSOR_TYPE_SALT,
    SENSOR_TYPE_INVALID_MEASUREMENT_COUNT,
)


class TestIsValueInRange:
    """Tests for the is_measurement_value_in_range helper."""

    def test_ph_valid_value(self):
        """pH of 7.2 is within 0-14."""
        assert is_measurement_value_in_range(SENSOR_TYPE_PH, 7.2) is True

    def test_ph_boundary_min(self):
        """pH of 0 is at the minimum boundary."""
        assert is_measurement_value_in_range(SENSOR_TYPE_PH, 0.0) is True

    def test_ph_boundary_max(self):
        """pH of 14 is at the maximum boundary."""
        assert is_measurement_value_in_range(SENSOR_TYPE_PH, 14.0) is True

    def test_ph_below_minimum(self):
        """Negative pH is below the valid range."""
        assert is_measurement_value_in_range(SENSOR_TYPE_PH, -1.0) is False

    def test_ph_above_maximum(self):
        """pH of 15 is above the valid range."""
        assert is_measurement_value_in_range(SENSOR_TYPE_PH, 15.0) is False

    def test_chlorine_valid(self):
        """Chlorine of 2.5 ppm is within 0-10."""
        assert is_measurement_value_in_range(SENSOR_TYPE_FREE_CL, 2.5) is True

    def test_chlorine_zero(self):
        """Chlorine of 0 is valid."""
        assert is_measurement_value_in_range(SENSOR_TYPE_FREE_CL, 0.0) is True

    def test_chlorine_above_maximum(self):
        """Chlorine of 50 ppm is clearly out of range."""
        assert is_measurement_value_in_range(SENSOR_TYPE_FREE_CL, 50.0) is False

    def test_chlorine_negative(self):
        """Negative chlorine is invalid."""
        assert is_measurement_value_in_range(SENSOR_TYPE_FREE_CL, -0.5) is False

    def test_bromine_valid(self):
        """Bromine of 4 ppm is within 0-13.5."""
        assert is_measurement_value_in_range(SENSOR_TYPE_BROMINE, 4.0) is True

    def test_bromine_boundary_max(self):
        """Bromine of 13.5 ppm is at the PoolLab range maximum."""
        assert is_measurement_value_in_range(SENSOR_TYPE_BROMINE, 13.5) is True

    def test_bromine_above_maximum(self):
        """Bromine above the PoolLab range is invalid."""
        assert is_measurement_value_in_range(SENSOR_TYPE_BROMINE, 14.0) is False

    def test_active_oxygen_valid(self):
        """Active oxygen of 8 ppm is within 0-30."""
        assert is_measurement_value_in_range(SENSOR_TYPE_ACTIVE_OXYGEN, 8.0) is True

    def test_active_oxygen_boundary_max(self):
        """Active oxygen of 30 ppm is at the PoolLab range maximum."""
        assert is_measurement_value_in_range(SENSOR_TYPE_ACTIVE_OXYGEN, 30.0) is True

    def test_active_oxygen_above_maximum(self):
        """Active oxygen above the PoolLab range is invalid."""
        assert is_measurement_value_in_range(SENSOR_TYPE_ACTIVE_OXYGEN, 31.0) is False

    def test_temperature_valid(self):
        """Temperature of 26°C is within 0-50."""
        assert is_measurement_value_in_range(SENSOR_TYPE_TEMP, 26.0) is True

    def test_temperature_below_minimum(self):
        """Temperature below 0°C is out of range for pool water."""
        assert is_measurement_value_in_range(SENSOR_TYPE_TEMP, -5.0) is False

    def test_temperature_above_maximum(self):
        """Temperature above 50°C is out of range for pool water."""
        assert is_measurement_value_in_range(SENSOR_TYPE_TEMP, 100.0) is False

    def test_alkalinity_valid(self):
        """Alkalinity of 100 ppm is within 0-300."""
        assert is_measurement_value_in_range(SENSOR_TYPE_ALK, 100.0) is True

    def test_alkalinity_above_maximum(self):
        """Alkalinity of 500 ppm is above the valid range."""
        assert is_measurement_value_in_range(SENSOR_TYPE_ALK, 500.0) is False

    def test_cya_valid(self):
        """CYA of 50 ppm is within 0-200."""
        assert is_measurement_value_in_range(SENSOR_TYPE_CYA, 50.0) is True

    def test_cya_above_maximum(self):
        """CYA of 300 ppm is above the valid range."""
        assert is_measurement_value_in_range(SENSOR_TYPE_CYA, 300.0) is False

    def test_salt_valid(self):
        """Salt of 1200 ppm is within 0-3600."""
        assert is_measurement_value_in_range(SENSOR_TYPE_SALT, 1200.0) is True

    def test_salt_above_maximum(self):
        """Salt of 5000 ppm is above the valid range."""
        assert is_measurement_value_in_range(SENSOR_TYPE_SALT, 5000.0) is False

    def test_unknown_sensor_type_is_always_valid(self):
        """Values for unknown sensor types have no min/max, so always valid."""
        assert is_measurement_value_in_range("unknown_sensor", 9999.0) is True


class TestMeasurementNativeValue:
    """Tests for sensor measurement value handling."""

    @staticmethod
    def _sensor(sensor_type: str, monkeypatch) -> object:
        sensor_component = ModuleType("homeassistant.components.sensor")
        sensor_component.SensorEntity = type("SensorEntity", (), {})
        sensor_component.SensorDeviceClass = SimpleNamespace(TIMESTAMP="timestamp")
        monkeypatch.setitem(sys.modules, "homeassistant.components.sensor", sensor_component)

        ha_const = ModuleType("homeassistant.const")
        ha_const.EntityCategory = SimpleNamespace(DIAGNOSTIC="diagnostic")
        ha_const.UnitOfTemperature = SimpleNamespace(CELSIUS="°C")
        monkeypatch.setitem(sys.modules, "homeassistant.const", ha_const)

        ha_core = ModuleType("homeassistant.core")
        ha_core.HomeAssistant = type("HomeAssistant", (), {})
        monkeypatch.setitem(sys.modules, "homeassistant.core", ha_core)

        entity_platform = ModuleType("homeassistant.helpers.entity_platform")
        entity_platform.AddEntitiesCallback = object
        monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_platform", entity_platform)

        update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
        update_coordinator.CoordinatorEntity = type("CoordinatorEntity", (), {})
        update_coordinator.DataUpdateCoordinator = type("DataUpdateCoordinator", (), {})
        update_coordinator.UpdateFailed = type("UpdateFailed", (Exception,), {})
        monkeypatch.setitem(sys.modules, "homeassistant.helpers.update_coordinator", update_coordinator)

        sys.modules.pop("poollab.sensor", None)
        sensor_module = importlib.import_module("poollab.sensor")

        PoollabSensor = sensor_module.PoollabSensor
        sensor = PoollabSensor.__new__(PoollabSensor)
        sensor.sensor_type = sensor_type
        return sensor

    def test_out_of_range_with_overrange_status_is_discarded(self, monkeypatch):
        """Non-numeric OVERANGE/OVERRANGE formatted status should be discarded."""
        sensor = self._sensor(SENSOR_TYPE_CYA, monkeypatch)
        measurement = {
            "value": 250,
            "formatted_value": "OVERRANGE",
        }

        assert sensor._measurement_native_value(measurement, "PL Cyanuric Acid") is None

    def test_out_of_range_with_overange_status_is_discarded(self, monkeypatch):
        """Non-numeric OVERANGE formatted status should be discarded."""
        sensor = self._sensor(SENSOR_TYPE_CYA, monkeypatch)
        measurement = {
            "value": 250,
            "formatted_value": "OVERANGE",
        }

        assert sensor._measurement_native_value(measurement, "PL Cyanuric Acid") is None

    def test_invalid_measurement_count_sensor_uses_coordinator_value(self, monkeypatch):
        """Invalid measurement count diagnostic should expose coordinator data."""
        sensor = self._sensor(SENSOR_TYPE_INVALID_MEASUREMENT_COUNT, monkeypatch)
        sensor.coordinator = SimpleNamespace(
            data={"invalid_measurement_count": 3},
            last_update_success=True,
        )

        assert sensor.native_value == 3
