"""Puhas integration."""
from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import PuhasClient
from .coordinator import PuhasConfigEntry, PuhasCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: PuhasConfigEntry) -> bool:
    """Set up Puhas from a config entry."""
    # Own session => own cookie jar, so the portal login never leaks elsewhere
    session = async_create_clientsession(hass)
    client = PuhasClient(session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = PuhasCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PuhasConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
