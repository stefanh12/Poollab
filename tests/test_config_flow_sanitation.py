"""Tests for sanitation selection helpers in config flow."""

import importlib
import sys
import types
from unittest.mock import MagicMock

from poollab.const import CONF_OPTION_DEVICES, CONF_SANITATION_MODE


def _load_config_flow_class():
    """Load PoollabConfigFlow with a lightweight ConfigFlow base stub."""
    class DummyConfigFlow:
        """Minimal ConfigFlow stub used for unit tests."""

        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__()

    homeassistant_module = types.ModuleType("homeassistant")

    config_entries_module = types.ModuleType("homeassistant.config_entries")
    config_entries_module.ConfigFlow = DummyConfigFlow

    const_module = types.ModuleType("homeassistant.const")
    const_module.CONF_TOKEN = "token"

    data_entry_flow_module = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow_module.FlowResult = dict

    aiohttp_client_module = types.ModuleType("homeassistant.helpers.aiohttp_client")

    def _async_get_clientsession(_hass):
        return None

    aiohttp_client_module.async_get_clientsession = _async_get_clientsession

    selector_module = types.ModuleType("homeassistant.helpers.selector")
    selector_module.SelectSelectorConfig = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
    selector_module.SelectOptionDict = lambda **kwargs: kwargs

    class _SelectSelectorMode:
        DROPDOWN = "dropdown"

    selector_module.SelectSelectorMode = _SelectSelectorMode
    selector_module.SelectSelector = lambda config: config

    helpers_module = types.ModuleType("homeassistant.helpers")
    helpers_module.selector = selector_module

    homeassistant_module.config_entries = config_entries_module

    sys.modules["homeassistant"] = homeassistant_module
    sys.modules["homeassistant.config_entries"] = config_entries_module
    sys.modules["homeassistant.const"] = const_module
    sys.modules["homeassistant.data_entry_flow"] = data_entry_flow_module
    sys.modules["homeassistant.helpers"] = helpers_module
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client_module
    sys.modules["homeassistant.helpers.selector"] = selector_module

    sys.modules.pop("poollab.config_flow", None)
    module = importlib.import_module("poollab.config_flow")
    module = importlib.reload(module)
    return module.PoollabConfigFlow


def test_build_device_descriptors_handles_id_collisions_and_labels():
    """Descriptor builder should mirror runtime ID rules and add serial labels."""
    PoollabConfigFlow = _load_config_flow_class()
    devices = [
        {
            "account": "My Account",
            "id": "id_1",
            "serialNumber": "SER-001",
            "name": "Main Pool",
        },
        {
            "account": "My Account",
            "id": "id_2",
            "serialNumber": "SER-002",
            "name": "Spa",
        },
    ]

    descriptors = PoollabConfigFlow._build_device_descriptors(devices)

    assert descriptors[0]["id"] == "My Account"
    assert descriptors[0]["label"] == "Main Pool (SER-001)"
    assert descriptors[1]["id"] == "SER-002"
    assert descriptors[1]["label"] == "Spa (SER-002)"


def test_begin_sanitation_selection_prefills_existing_modes_for_matching_devices():
    """Only modes for currently discovered devices should be prefilled."""
    PoollabConfigFlow = _load_config_flow_class()
    flow = PoollabConfigFlow()
    devices = [
        {"account": "Pool A", "id": "id_a", "serialNumber": "S-A", "name": "Pool A"},
        {"account": "Pool B", "id": "id_b", "serialNumber": "S-B", "name": "Pool B"},
    ]
    existing_options = {
        CONF_OPTION_DEVICES: {
            "Pool A": {CONF_SANITATION_MODE: "chlorine"},
            "old-device": {CONF_SANITATION_MODE: "bromine_active_oxygen"},
        }
    }

    flow._begin_sanitation_selection(
        token="abc",
        devices=devices,
        reconfigure_entry_id="entry123",
        existing_options=existing_options,
    )

    assert flow._pending_token == "abc"
    assert flow._target_entry_id == "entry123"
    assert len(flow._pending_devices) == 2
    assert flow._selected_sanitation_modes == {"Pool A": "chlorine"}


def test_finish_sanitation_selection_creates_entry_with_options_map():
    """Initial setup should write sanitation modes into entry options."""
    PoollabConfigFlow = _load_config_flow_class()
    flow = PoollabConfigFlow()
    flow._pending_token = "abc"
    flow._selected_sanitation_modes = {
        "Pool A": "chlorine",
        "S-B": "bromine_active_oxygen",
    }

    captured = {}

    def _create_entry(**kwargs):
        captured.update(kwargs)
        return kwargs

    flow.async_create_entry = _create_entry

    result = flow._finish_sanitation_selection()

    assert result["data"]
    assert result["options"][CONF_OPTION_DEVICES]["Pool A"][CONF_SANITATION_MODE] == "chlorine"
    assert (
        result["options"][CONF_OPTION_DEVICES]["S-B"][CONF_SANITATION_MODE]
        == "bromine_active_oxygen"
    )


def test_finish_sanitation_selection_updates_reconfigure_options():
    """Reconfigure should merge options and replace per-device sanitation map."""
    PoollabConfigFlow = _load_config_flow_class()
    flow = PoollabConfigFlow()
    flow._pending_token = "new-token"
    flow._target_entry_id = "entry123"
    flow._selected_sanitation_modes = {"Pool A": "chlorine"}

    reconfigure_entry = MagicMock()
    reconfigure_entry.options = {"foo": "bar", CONF_OPTION_DEVICES: {"old": {}}}

    flow.hass = MagicMock()
    flow.hass.config_entries.async_get_entry.return_value = reconfigure_entry

    update_entry_calls = {}

    def _update_entry(entry, **kwargs):
        update_entry_calls["entry"] = entry
        update_entry_calls.update(kwargs)

    flow.hass.config_entries.async_update_entry = _update_entry

    def _update_reload(entry, data_updates):
        return {
            "entry": entry,
            "data_updates": data_updates,
        }

    flow.async_update_reload_and_abort = _update_reload

    result = flow._finish_sanitation_selection()

    assert result["entry"] == reconfigure_entry
    assert update_entry_calls["entry"] == reconfigure_entry
    assert update_entry_calls["options"]["foo"] == "bar"
    assert update_entry_calls["options"][CONF_OPTION_DEVICES] == {
        "Pool A": {CONF_SANITATION_MODE: "chlorine"}
    }
