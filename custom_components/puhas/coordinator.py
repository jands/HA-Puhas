"""Data update coordinator."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PuhasAuthError, PuhasClient, PuhasConnectionError, PuhasData
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type PuhasConfigEntry = ConfigEntry[PuhasCoordinator]


class PuhasCoordinator(DataUpdateCoordinator[PuhasData]):
    """Fetch data from the Puhas portal."""

    config_entry: PuhasConfigEntry

    def __init__(self, hass: HomeAssistant, entry: PuhasConfigEntry, client: PuhasClient) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL, config_entry=entry
        )
        self.client = client

    async def _async_update_data(self) -> PuhasData:
        try:
            return await self.client.async_fetch()
        except PuhasAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except PuhasConnectionError as err:
            raise UpdateFailed(str(err)) from err
