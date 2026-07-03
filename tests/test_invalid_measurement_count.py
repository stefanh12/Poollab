"""Tests for invalid measurement counting."""

from poollab.coordinator import _count_invalid_measurements


def test_count_invalid_measurements_counts_out_of_range_and_non_numeric_values():
    """Out-of-range and non-numeric values should be counted."""
    measurements = [
        {"parameter": "PL pH", "value": 7.2},
        {"parameter": "PL Cyanuric Acid", "value": 250, "formatted_value": "OVERRANGE"},
        {"parameter": "PL Active Oxygen (MPS)", "value": "invalid"},
        {"parameter": "Unknown Parameter", "value": 999},
    ]

    assert _count_invalid_measurements(measurements) == 2


def test_count_invalid_measurements_supports_alternate_parameter_names():
    """Alternate LabCom parameter names should be validated too."""
    measurements = [
        {"parameter": "PL Chlorine Total", "value": 11},
        {"parameter": "PL Alkalinity", "value": 120},
        {"parameter": "PL Aktivsauerstoff", "value": 31},
    ]

    assert _count_invalid_measurements(measurements) == 2
