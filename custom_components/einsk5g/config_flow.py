"""Config flow for 1KOMMA5GRAD integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EinsK5GApi, EinsK5GAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class EinsK5GConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 1KOMMA5GRAD."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate credentials
                session = async_get_clientsession(self.hass)
                api = EinsK5GApi(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=session,
                )

                # Try to authenticate
                await api.authenticate()

                # Get systems to verify access and get system info
                systems = await api.get_systems()

                if not systems:
                    errors["base"] = "no_systems"
                else:
                    system = systems[0]
                    system_id = system.get("id")
                    system_name = system.get("systemName", "1KOMMA5GRAD")

                    # Check for existing entry with same system
                    await self.async_set_unique_id(system_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=system_name,
                        data={
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            "system_id": system_id,
                        },
                    )

            except EinsK5GAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                api = EinsK5GApi(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=session,
                )

                await api.authenticate()

                # Update the config entry
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                if entry:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)

                return self.async_abort(reason="reauth_successful")

            except EinsK5GAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during re-auth")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
