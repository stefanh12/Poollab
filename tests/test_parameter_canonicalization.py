"""Tests for locale-independent measurement parameter canonicalization."""

import pytest
from poollab.coordinator import _canonicalize_parameter_name


@pytest.mark.parametrize(
    ("raw_name", "canonical_name"),
    [
        ("pH", "PL pH"),
        (" free chlorine ", "PL Chlorine Free"),
        ("PL Chlorine Total", "PL Total Chlorine"),
        ("Temperature", "PL Temperature"),
        ("Aktivsauerstoff (MPS)", "PL Active Oxygen"),
        ("PL MPS", "PL Active Oxygen"),
        ("Alkalinity", "PL T-Alka"),
    ],
)
def test_parameter_aliases_use_canonical_names(raw_name, canonical_name):
    """Manual and localized labels should resolve to sensor lookup keys."""
    assert _canonicalize_parameter_name(raw_name) == canonical_name


@pytest.mark.parametrize("raw_name", [None, "", "Custom Lab Measurement"])
def test_unknown_parameter_names_are_preserved(raw_name):
    """Unknown or empty labels should not be invented or discarded."""
    assert _canonicalize_parameter_name(raw_name) == raw_name
