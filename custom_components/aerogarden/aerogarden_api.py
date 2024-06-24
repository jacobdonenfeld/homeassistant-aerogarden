import base64
import json
import logging
import urllib.parse

import aiohttp
import async_timeout

from .const import (
    DEFAULT_HOST,
    LOGIN_URL,
    STATUS_URL,
    UPDATE_URL,
    ERROR_AUTH,
    ERROR_CONNECTION,
)

_LOGGER = logging.getLogger(__name__)

class AerogardenAPI:
    """API class for interacting with Aerogarden."""

    def __init__(self, username, password, host=DEFAULT_HOST, session=None):
        """Initialize the API."""
        self._username = urllib.parse.quote(username)
        self._password = urllib.parse.quote(password)
        self._host = host
        self._userid = None
        self._session = session or aiohttp.ClientSession()
        self._headers = {
            "User-Agent": "HA-Aerogarden/0.3",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self._data = {}

    async def login(self):
        """Authenticate with the Aerogarden API."""
        post_data = f"mail={self._username}&userPwd={self._password}"
        url = f"{self._host}{LOGIN_URL}"

        try:
            async with async_timeout.timeout(10):
                async with self._session.post(url, data=post_data, headers=self._headers) as response:
                    response.raise_for_status()
                    data = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            _LOGGER.error("Error communicating with Aerogarden servers: %s", ex)
            raise ConnectionError(ERROR_CONNECTION)

        userid = data.get("code")
        if userid and userid > 0:
            self._userid = str(userid)
            return True
        else:
            _LOGGER.error("Login failed: %s", data.get("msg", "Unknown error"))
            raise ValueError(ERROR_AUTH)

    async def fetch_data(self):
        """Fetch the latest data from the Aerogarden API."""
        if not self._userid:
            await self.login()

        url = f"{self._host}{STATUS_URL}"
        post_data = f"userID={self._userid}"

        try:
            async with async_timeout.timeout(10):
                async with self._session.post(url, data=post_data, headers=self._headers) as response:
                    response.raise_for_status()
                    garden_data = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            _LOGGER.error("Error fetching garden data: %s", ex)
            raise ConnectionError(ERROR_CONNECTION)

        if "Message" in garden_data:
            error_msg = f"Failed to get garden data: {garden_data['Message']}"
            _LOGGER.error(error_msg)
            raise ValueError(error_msg)

        new_data = {}
        for garden in garden_data:
            if "plantedName" in garden:
                garden["plantedName"] = base64.b64decode(garden["plantedName"]).decode("utf-8")

            garden_id = garden.get("configID")
            garden_mac = f"{garden['airGuid']}{'-' + str(garden_id) if garden_id else ''}"
            new_data[garden_mac] = garden

        self._data = new_data
        return new_data

    async def light_toggle(self, macaddr):
        """Toggle the light state of a garden."""
        if macaddr not in self._data:
            _LOGGER.error("light_toggle called for unknown macaddr: %s", macaddr)
            return False

        post_data = json.dumps({
            "airGuid": macaddr,
            "chooseGarden": self._data[macaddr].get("chooseGarden"),
            "userID": self._userid,
            "plantConfig": json.dumps({"lightTemp": self._data[macaddr].get("lightTemp")})
        })
        url = f"{self._host}{UPDATE_URL}"

        try:
            async with async_timeout.timeout(10):
                async with self._session.post(url, data=post_data, headers=self._headers) as response:
                    response.raise_for_status()
                    data = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            _LOGGER.error("Error toggling light: %s", ex)
            return False

        if data.get("code") == 1:
            await self.fetch_data()  # Update data after successful toggle
            return True

        _LOGGER.error("Failed to toggle light: %s", data.get('msg', 'Unknown error'))
        return False

    async def close(self):
        """Close the session."""
        await self._session.close()