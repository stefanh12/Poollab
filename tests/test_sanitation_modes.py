"""Tests for sanitation mode sensor exposure."""

from poollab.const import (
    SANITATION_MODE_BROMINE_ACTIVE_OXYGEN,
    SANITATION_MODE_CHLORINE,
    SENSOR_TYPE_ACTIVE_OXYGEN,
    SENSOR_TYPE_BROMINE,
    SENSOR_TYPE_CL,
    SENSOR_TYPE_COMBINED_CL,
    SENSOR_TYPE_FREE_CL,
    SENSOR_TYPE_LAST_MEASUREMENT,
    SENSOR_TYPE_MEASUREMENT_COUNT,
    SENSOR_TYPE_PH,
    SENSOR_TYPE_TOTAL_CL,
    get_sensor_types_for_sanitation,
)


def test_chlorine_mode_exposes_chlorine_family_sensors():
    """Chlorine mode should expose chlorine-related sensors and diagnostics."""
    sensor_types = get_sensor_types_for_sanitation(SANITATION_MODE_CHLORINE)

    assert SENSOR_TYPE_PH in sensor_types
    assert SENSOR_TYPE_CL in sensor_types
    assert SENSOR_TYPE_FREE_CL in sensor_types
    assert SENSOR_TYPE_TOTAL_CL in sensor_types
    assert SENSOR_TYPE_COMBINED_CL in sensor_types
    assert SENSOR_TYPE_BROMINE not in sensor_types
    assert SENSOR_TYPE_ACTIVE_OXYGEN not in sensor_types
    assert SENSOR_TYPE_MEASUREMENT_COUNT in sensor_types
    assert SENSOR_TYPE_LAST_MEASUREMENT in sensor_types


def test_bromine_active_oxygen_mode_exposes_bromine_and_oxygen_sensors():
    """Bromine+oxygen mode should hide chlorine-family sensors."""
    sensor_types = get_sensor_types_for_sanitation(
        SANITATION_MODE_BROMINE_ACTIVE_OXYGEN
    )

    assert SENSOR_TYPE_PH in sensor_types
    assert SENSOR_TYPE_BROMINE in sensor_types
    assert SENSOR_TYPE_ACTIVE_OXYGEN in sensor_types
    assert SENSOR_TYPE_CL not in sensor_types
    assert SENSOR_TYPE_FREE_CL not in sensor_types
    assert SENSOR_TYPE_TOTAL_CL not in sensor_types
    assert SENSOR_TYPE_COMBINED_CL not in sensor_types
    assert SENSOR_TYPE_MEASUREMENT_COUNT in sensor_types
    assert SENSOR_TYPE_LAST_MEASUREMENT in sensor_types
