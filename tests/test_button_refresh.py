"""Tests for Poollab manual refresh button entities."""

import asyncio
import importlib
import sys
import types

from poollab.const import UPDATE_MODE_MANUAL, UPDATE_MODE_POLLING


def _load_button_module():
    """Load button module with lightweight HA stubs."""
    button_module = types.ModuleType("homeassistant.components.button")

    class DummyButtonEntity:
        """Minimal ButtonEntity stub."""

    button_module.ButtonEntity = DummyButtonEntity

    core_module = types.ModuleType("homeassistant.core")
    core_module.HomeAssistant = object

    entity_platform_module = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform_module.AddEntitiesCallback = object

    update_coordinator_module = types.ModuleType("homeassistant.helpers.update_coordinator")

    class DummyCoordinatorEntity:
        """Minimal CoordinatorEntity stub."""

        def __init__(self, coordinator):
            self.coordinator = coordinator

    update_coordinator_module.CoordinatorEntity = DummyCoordinatorEntity

    sys.modules["homeassistant.components.button"] = button_module
    sys.modules["homeassistant.core"] = core_module
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_module
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator_module

    sys.modules.pop("poollab.button", None)
    module = importlib.import_module("poollab.button")
    return importlib.reload(module)


class _FakeCoordinator:
    """Coordinator stub that tracks refresh calls."""

    def __init__(self):
        self.refresh_calls = 0

    async def async_request_refresh(self):
        self.refresh_calls += 1


def test_refresh_button_press_requests_coordinator_refresh():
    """Pressing the button should force a coordinator refresh."""
    module = _load_button_module()

    coordinator = _FakeCoordinator()
    button = module.PoollabRefreshButton(
        coordinator,
        types.SimpleNamespace(entry_id="entry-1"),
        "device-1",
        "Main Pool",
    )

    asyncio.run(button.async_press())

    assert coordinator.refresh_calls == 1


def test_button_platform_adds_only_manual_mode_buttons():
    """Button entities should be created only for manual update mode devices."""
    module = _load_button_module()

    coordinators = {
        "device-manual": {
            "coordinator": _FakeCoordinator(),
            "name": "Manual Pool",
            "update_mode": UPDATE_MODE_MANUAL,
        },
        "device-polling": {
            "coordinator": _FakeCoordinator(),
            "name": "Polling Pool",
            "update_mode": UPDATE_MODE_POLLING,
        },
    }

    hass = types.SimpleNamespace(
        data={
            "poollab": {
                "entry-1": {
                    "coordinators": coordinators,
                }
            }
        }
    )
    entry = types.SimpleNamespace(entry_id="entry-1")

    added_entities = []

    def _add_entities(entities, _update_before_add):
        added_entities.extend(entities)

    asyncio.run(module.async_setup_entry(hass, entry, _add_entities))

    assert len(added_entities) == 1
    assert added_entities[0]._attr_unique_id == "entry-1_device-manual_refresh"
