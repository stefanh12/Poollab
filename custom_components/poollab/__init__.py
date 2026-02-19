"""The Poollab integration."""

import asyncio
import logging
from typing import Final

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PoollabApiClient
from .coordinator import PoollabDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Poollab from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)

    _LOGGER.info("Initializing Poollab API client from token")
    api_client = PoollabApiClient(
        entry.data[CONF_TOKEN],
        session,
    )

    # Verify token is valid
    _LOGGER.debug("Verifying Poollab API token")
    try:
        if not await asyncio.wait_for(api_client.verify_token(), timeout=30.0):
            _LOGGER.error("Invalid Poollab API token")
            return False
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout verifying Poollab API token")
        return False
    except Exception as err:
        _LOGGER.error("Error verifying API token: %s", err, exc_info=True)
        return False

    _LOGGER.info("Poollab API token verified successfully")

    # Get all devices/accounts (pools)
    _LOGGER.debug("Fetching devices from Poollab API")
    try:
        devices = await asyncio.wait_for(api_client.get_devices(), timeout=30.0)
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout fetching devices from Poollab API")
        return False
    except Exception as err:
        _LOGGER.error("Error fetching devices: %s", err, exc_info=True)
        return False

    if not devices:
        _LOGGER.error("No devices found in Poollab account")
        return False

    _LOGGER.info("Found %d device(s) in Poollab account", len(devices))

    # Set up data update coordinator for each device
    coordinators = {}
    for device_idx, device in enumerate(devices):
        # Use account name as device_id since it uniquely identifies each pool
        device_id = device.get("account") or device.get("id")
        device_name = device.get("name", f"Pool {device_idx + 1}")

        if not device_id:
            _LOGGER.warning("Could not determine device ID for %s", device_name)
            continue

        _LOGGER.info("Setting up device: %s (Account: %s)", device_name, device_id)

        # Create coordinator for this device
        coordinator = PoollabDataUpdateCoordinator(hass, api_client, device_id)

        # Initial data fetch with timeout
        try:
            await asyncio.wait_for(
                coordinator.async_config_entry_first_refresh(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "Timeout during initial refresh for device %s, continuing anyway",
                device_id
            )
        except Exception as err:
            _LOGGER.warning(
                "Error during initial refresh for device %s: %s, continuing anyway",
                device_id,
                err
            )

        coordinators[device_id] = {
            "coordinator": coordinator,
            "device": device,
            "name": device_name,
        }

    if not coordinators:
        _LOGGER.error("No valid devices found to set up")
        return False

    # Store all device data
    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api_client,
        "coordinators": coordinators,
        "devices": devices,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up options flow
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        api_client = hass.data[DOMAIN][entry.entry_id]["api_client"]
        await api_client.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Poollab component."""
    hass.data.setdefault(DOMAIN, {})
    return True
