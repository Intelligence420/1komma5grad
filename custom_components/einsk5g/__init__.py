"""The 1KOMMA5GRAD integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EinsK5GApi, EinsK5GApiError, EinsK5GAuthError
from .const import DOMAIN
from .coordinator import EinsK5GDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up 1KOMMA5GRAD from a config entry."""
    session = async_get_clientsession(hass)

    api = EinsK5GApi(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=session,
    )

    try:
        # Authenticate with the API
        await api.authenticate()

        # Get systems
        systems = await api.get_systems()
        if not systems:
            raise ConfigEntryNotReady("No systems found")

        system = systems[0]
        system_id = system.get("id", entry.data.get("system_id"))

    except EinsK5GAuthError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except EinsK5GApiError as err:
        raise ConfigEntryNotReady(f"Failed to connect: {err}") from err

    # Create the data coordinator
    coordinator = EinsK5GDataUpdateCoordinator(hass, api, system_id)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator and API
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "system_id": system_id,
        "system_info": system,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        api: EinsK5GApi = data["api"]
        await api.close()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
