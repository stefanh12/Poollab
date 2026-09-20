"""Tests for the calcium hardness and total hardness sensors."""

import importlib
import sys
from types import ModuleType, SimpleNamespace

from poollab.const import (
    SANITATION_MODE_BROMINE_ACTIVE_OXYGEN,
    SANITATION_MODE_CHLORINE,
    SENSOR_CONFIGS,
    SENSOR_TYPE_CALCIUM_HARDNESS,
    SENSOR_TYPE_TOTAL_HARDNESS,
    get_sensor_types_for_sanitation,
    is_measurement_value_in_range,
)
from poollab.coordinator import (
    MEASUREMENT_SENSOR_TYPES,
    _canonicalize_parameter_name,
    _count_invalid_measurements,
)

HARDNESS_SENSOR_TYPES = (SENSOR_TYPE_CALCIUM_HARDNESS, SENSOR_TYPE_TOTAL_HARDNESS)


def test_hardness_sensors_report_whole_ppm_values():
    """Both hardness sensors use ppm (mg/l as CaCO3) without decimals."""
    for sensor_type in HARDNESS_SENSOR_TYPES:
        config = SENSOR_CONFIGS[sensor_type]
        assert config["unit"] == "ppm"
        assert config["precision"] == 0
        assert config["min"] == 0
        assert config["max"] == 2000


def test_hardness_sensors_exist_in_every_sanitation_mode():
    """Hardness does not depend on the sanitizer, so both modes expose the sensors."""
    for mode in (SANITATION_MODE_CHLORINE, SANITATION_MODE_BROMINE_ACTIVE_OXYGEN):
        sensor_types = get_sensor_types_for_sanitation(mode)
        assert SENSOR_TYPE_CALCIUM_HARDNESS in sensor_types
        assert SENSOR_TYPE_TOTAL_HARDNESS in sensor_types


def test_hardness_range_validation():
    """Typical pool values are valid, negative or absurd values are not."""
    assert is_measurement_value_in_range(SENSOR_TYPE_CALCIUM_HARDNESS, 174.0) is True
    assert is_measurement_value_in_range(SENSOR_TYPE_TOTAL_HARDNESS, 2000.0) is True
    assert is_measurement_value_in_range(SENSOR_TYPE_CALCIUM_HARDNESS, -1.0) is False
    assert is_measurement_value_in_range(SENSOR_TYPE_TOTAL_HARDNESS, 2500.0) is False


def test_labcom_parameter_names_map_to_hardness_sensors():
    """Device measurements carry the "PL " prefix and map to the new sensor types."""
    assert MEASUREMENT_SENSOR_TYPES["PL Calcium Hardness"] == SENSOR_TYPE_CALCIUM_HARDNESS
    assert MEASUREMENT_SENSOR_TYPES["PL Total Hardness"] == SENSOR_TYPE_TOTAL_HARDNESS


def test_manual_hardness_entries_are_canonicalized():
    """Values entered manually on labcom.cloud lack the "PL " prefix."""
    assert _canonicalize_parameter_name("Calcium Hardness") == "PL Calcium Hardness"
    assert _canonicalize_parameter_name("total hardness") == "PL Total Hardness"
    assert _canonicalize_parameter_name("PL Total Hardness") == "PL Total Hardness"


def test_overrange_hardness_counts_as_invalid_measurement():
    """An OVERRANGE hardness reading (1000000) is counted like other invalid readings."""
    measurements = [
        {"parameter": "PL Calcium Hardness", "value": "174.17746"},
        {"parameter": "PL Total Hardness", "value": "1000000"},
    ]

    assert _count_invalid_measurements(measurements) == 1


class TestHardnessNativeValue:
    """The sensor entity reads hardness measurements like any other parameter."""

    @staticmethod
    def _sensor(sensor_type: str, monkeypatch) -> object:
        """Import poollab.sensor with minimal Home Assistant stubs and build a bare sensor."""
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

        sensor = sensor_module.PoollabSensor.__new__(sensor_module.PoollabSensor)
        sensor.sensor_type = sensor_type
        return sensor

    def test_calcium_hardness_is_rounded_to_whole_ppm(self, monkeypatch):
        """A raw Labcom value of 174.17746 mg/l is reported as 174."""
        sensor = self._sensor(SENSOR_TYPE_CALCIUM_HARDNESS, monkeypatch)
        sensor.coordinator = SimpleNamespace(
            data={
                "latest_values": {
                    "PL Calcium Hardness": {"value": "174.17746", "unit": "mg/l CaCO₃"},
                },
                "active_chlorine": {},
            },
            last_update_success=True,
        )

        assert sensor.native_value == 174.0

    def test_total_hardness_without_measurement_is_none(self, monkeypatch):
        """A device that never measured total hardness reports no value."""
        sensor = self._sensor(SENSOR_TYPE_TOTAL_HARDNESS, monkeypatch)
        sensor.coordinator = SimpleNamespace(
            data={"latest_values": {}, "active_chlorine": {}},
            last_update_success=True,
        )

        assert sensor.native_value is None
