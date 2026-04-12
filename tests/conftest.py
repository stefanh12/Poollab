"""Configuration constants for tests."""

import sys
import os
from unittest.mock import MagicMock
import pytest

# Create a mock homeassistant module and its submodules before importing poollab
ha_mock = MagicMock()
sys.modules['homeassistant'] = ha_mock
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()

# Mock helpers and its submodules
helpers_mock = MagicMock()
sys.modules['homeassistant.helpers'] = helpers_mock
sys.modules['homeassistant.helpers.config_validation'] = MagicMock()
sys.modules['homeassistant.helpers.aiohttp_client'] = MagicMock()
sys.modules['homeassistant.helpers.update_coordinator'] = MagicMock()
sys.modules['homeassistant.helpers.entity'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()

# Add custom_components to the path so poollab can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components'))

TEST_TOKEN = "e3ce8106035d4196066e33f2ef8a313ed3f7f57d836b7e5cca212509dbaccb7fa3c4ca0b8db5905b"
TEST_DEVICE_ID = "device_123"
