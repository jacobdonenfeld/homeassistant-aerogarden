import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AerogardenAPI
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AerogardenDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Aerogarden data."""

    def __init__(self, hass: HomeAssistant, api: AerogardenAPI):
        """Initialize the data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch data from the Aerogarden API."""
        try:
            return await self.api.fetch_data()
        except ConnectionError as error:
            raise UpdateFailed(f"Error communicating with API: {error}")
        except ValueError as error:
            raise UpdateFailed(f"Invalid data received from API: {error}")
