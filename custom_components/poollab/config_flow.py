"""Config flow for Poollab integration."""

import asyncio
import logging
from typing import Any, Dict, Optional
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import PoollabApiClient
from .const import (
    CONF_OPTION_DEVICES,
    CONF_SANITATION_MODE,
    DOMAIN,
    SANITATION_MODE_BROMINE_ACTIVE_OXYGEN,
    SANITATION_MODE_CHLORINE,
)

_LOGGER = logging.getLogger(__name__)


class PoollabConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Poollab."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._pending_token: Optional[str] = None
        self._pending_devices: list[dict[str, Any]] = []
        self._selected_sanitation_modes: dict[str, str] = {}
        self._device_selection_index = 0
        self._reconfigure_entry_id: Optional[str] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_TOKEN][:16])
            self._abort_if_unique_id_configured()

            # Try to authenticate
            try:
                session = async_get_clientsession(self.hass)
                api_client = PoollabApiClient(
                    user_input[CONF_TOKEN],
                    session,
                )

                if await api_client.verify_token():
                    devices = await api_client.get_devices()
                    if devices:
                        self._begin_sanitation_selection(
                            token=user_input[CONF_TOKEN],
                            devices=devices,
                        )
                        return await self.async_step_sanitation()
                    errors["base"] = "no_devices"
                else:
                    errors["base"] = "invalid_auth"
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.error("Unexpected error: %s", err)
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "token_url": "https://labcom.cloud/pages/user-setting"
            },
        )

    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_data)

    async def async_step_reconfigure(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reconfiguration of an existing config entry."""
        errors: Dict[str, str] = {}
        reconfigure_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            token = user_input[CONF_TOKEN]

            try:
                session = async_get_clientsession(self.hass)
                api_client = PoollabApiClient(token, session)

                if await api_client.verify_token():
                    devices = await api_client.get_devices()
                    if devices:
                        self._begin_sanitation_selection(
                            token=token,
                            devices=devices,
                            reconfigure_entry_id=reconfigure_entry.entry_id,
                            existing_options=reconfigure_entry.options,
                        )
                        return await self.async_step_sanitation()
                    errors["base"] = "no_devices"
                else:
                    errors["base"] = "invalid_auth"
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.error("Unexpected error during reconfigure: %s", err)
                errors["base"] = "unknown"

        current_token = reconfigure_entry.data.get(CONF_TOKEN, "")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN, default=current_token): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "token_url": "https://labcom.cloud/pages/user-setting"
            },
        )

    async def async_step_sanitation(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Collect sanitation mode for each discovered device."""
        if not self._pending_token or not self._pending_devices:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            current_device = self._pending_devices[self._device_selection_index]
            self._selected_sanitation_modes[current_device["id"]] = user_input[CONF_SANITATION_MODE]
            self._device_selection_index += 1

            if self._device_selection_index >= len(self._pending_devices):
                return self._finish_sanitation_selection()

        current_device = self._pending_devices[self._device_selection_index]
        current_mode = self._selected_sanitation_modes.get(current_device["id"])

        selector_config = selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(
                    value=SANITATION_MODE_CHLORINE,
                    label="Chlorine",
                ),
                selector.SelectOptionDict(
                    value=SANITATION_MODE_BROMINE_ACTIVE_OXYGEN,
                    label="Bromine + Active Oxygen",
                ),
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )

        field = vol.Required(CONF_SANITATION_MODE)
        if current_mode is not None:
            field = vol.Required(CONF_SANITATION_MODE, default=current_mode)

        data_schema = vol.Schema(
            {
                field: selector.SelectSelector(selector_config),
            }
        )

        return self.async_show_form(
            step_id="sanitation",
            data_schema=data_schema,
            errors={},
            description_placeholders={
                "device_name": current_device["label"],
                "current_index": str(self._device_selection_index + 1),
                "total_devices": str(len(self._pending_devices)),
            },
        )

    def _begin_sanitation_selection(
        self,
        token: str,
        devices: list[dict[str, Any]],
        reconfigure_entry_id: Optional[str] = None,
        existing_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize sanitation selection state and open sanitation step."""
        self._pending_token = token
        self._pending_devices = self._build_device_descriptors(devices)
        self._device_selection_index = 0
        self._reconfigure_entry_id = reconfigure_entry_id

        previous_modes = {}
        if existing_options:
            previous_devices = existing_options.get(CONF_OPTION_DEVICES, {})
            previous_modes = {
                device_id: device_config.get(CONF_SANITATION_MODE)
                for device_id, device_config in previous_devices.items()
                if isinstance(device_config, dict)
            }

        self._selected_sanitation_modes = {
            device["id"]: previous_modes[device["id"]]
            for device in self._pending_devices
            if device["id"] in previous_modes and previous_modes[device["id"]]
        }

    def _finish_sanitation_selection(self) -> FlowResult:
        """Persist selected sanitation modes and finish flow."""
        device_options = {
            device_id: {CONF_SANITATION_MODE: mode}
            for device_id, mode in self._selected_sanitation_modes.items()
        }

        if self._reconfigure_entry_id:
            reconfigure_entry = self.hass.config_entries.async_get_entry(self._reconfigure_entry_id)
            if reconfigure_entry is None:
                return self.async_abort(reason="unknown")

            options_updates = {
                **reconfigure_entry.options,
                CONF_OPTION_DEVICES: device_options,
            }
            return self.async_update_reload_and_abort(
                reconfigure_entry,
                data_updates={CONF_TOKEN: self._pending_token},
                options_updates=options_updates,
            )

        return self.async_create_entry(
            title="Poollab",
            data={CONF_TOKEN: self._pending_token},
            options={CONF_OPTION_DEVICES: device_options},
        )

    @staticmethod
    def _build_device_descriptors(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build stable device descriptors with IDs matching runtime setup logic."""
        descriptors: list[dict[str, Any]] = []
        used_ids: set[str] = set()

        for device_idx, device in enumerate(devices):
            primary_id = device.get("account") or device.get("id")
            fallback_id = device.get("serialNumber") or device.get("id")
            device_id = str(primary_id) if primary_id is not None else None
            fallback_id_str = str(fallback_id) if fallback_id is not None else None
            if not device_id and fallback_id_str:
                device_id = fallback_id_str

            if device_id in used_ids and fallback_id_str:
                device_id = fallback_id_str

            if not device_id:
                continue

            used_ids.add(device_id)
            device_name = device.get("name", f"Pool {device_idx + 1}")
            serial = device.get("serialNumber")
            label = device_name
            if serial:
                label = f"{label} ({serial})"

            descriptors.append(
                {
                    "id": str(device_id),
                    "label": label,
                }
            )

        return descriptors

