"""Config flow for Poollab integration."""

import asyncio
import logging
from typing import Any, Dict, Optional
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PoollabApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PoollabConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Poollab."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return PoollabOptionsFlow()

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
                        return self.async_create_entry(
                            title="Poollab",
                            data=user_input,
                        )
                    else:
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
                "token_url": "https://backend.labcom.cloud/graphiql"
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
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            token = user_input[CONF_TOKEN]

            try:
                session = async_get_clientsession(self.hass)
                api_client = PoollabApiClient(token, session)

                if await api_client.verify_token():
                    devices = await api_client.get_devices()
                    if devices:
                        updated_options = dict(reconfigure_entry.options)
                        updated_options[CONF_TOKEN] = token

                        return self.async_update_reload_and_abort(
                            reconfigure_entry,
                            data_updates={CONF_TOKEN: token},
                            options=updated_options,
                        )
                    errors["base"] = "no_devices"
                else:
                    errors["base"] = "invalid_auth"
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.error("Unexpected error during reconfigure: %s", err)
                errors["base"] = "unknown"

        current_token = reconfigure_entry.options.get(
            CONF_TOKEN,
            reconfigure_entry.data.get(CONF_TOKEN, ""),
        )

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
                "token_url": "https://backend.labcom.cloud/graphiql"
            },
        )


class PoollabOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Poollab."""

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_token = self.config_entry.options.get(
            CONF_TOKEN,
            self.config_entry.data.get(CONF_TOKEN, ""),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", 300),
                ): int,
                vol.Optional(
                    CONF_TOKEN,
                    default=current_token,
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
