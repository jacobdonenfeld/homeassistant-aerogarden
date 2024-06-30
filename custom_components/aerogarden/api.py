import asyncio
import base64
import json
import logging
from typing import Any, Dict, Optional

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import Throttle

from .const import MIN_TIME_BETWEEN_UPDATES

_LOGGER = logging.getLogger(__name__)


class AerogardenAPI:
    def __init__(self, hass: HomeAssistant, username: str, password: str, host: str):
        self._hass = hass
        self._username = username
        self._password = password
        self._host = host
        self._userid: Optional[str] = None
        self._error_msg: Optional[str] = None
        self._data: Dict[str, Any] = {}

        self._login_url = f"{self._host}/api/Admin/Login"
        self._status_url = f"{self._host}/api/CustomData/QueryUserDevice"
        self._update_url = f"{self._host}/api/Custom/UpdateDeviceConfig"

        self._headers = {
            "User-Agent": "HA-Aerogarden/0.1",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    @property
    def error(self) -> Optional[str]:
        return self._error_msg

    async def login(self) -> bool:
        post_data = f"mail={self._username}&userPwd={self._password}"
        response = await self._post_request(self._login_url, post_data)

        if not response:
            _LOGGER.error("Issue logging into Aerogarden servers.")
            return False

        userid = response.get("code")
        if userid and userid > 0:
            self._userid = str(userid)
            return True
        else:
            self._error_msg = f"Login API call returned {response.get('code')}"
            _LOGGER.error(self._error_msg)
            return False

    def is_valid_login(self) -> bool:
        return self._userid is not None

    def garden_name(self, macaddr: str) -> Optional[str]:
        multi_garden = self.garden_property(macaddr, "chooseGarden")
        if multi_garden is None:
            return self.garden_property(macaddr, "plantedName")
        multi_garden_label = "left" if multi_garden == 0 else "right"
        return f"{self.garden_property(macaddr, 'plantedName')}_{multi_garden_label}"

    def garden_property(self, macaddr: str, field: str) -> Any:
        return self._data.get(macaddr, {}).get(field)

    async def light_toggle(self, macaddr: str) -> bool:
        if macaddr not in self._data:
            _LOGGER.debug(f"light_toggle called for unknown macaddr: {macaddr}")
            return False

        post_data = json.dumps(
            {
                "airGuid": macaddr,
                "chooseGarden": self.garden_property(macaddr, "chooseGarden"),
                "userID": self._userid,
                "plantConfig": f'{{ "lightTemp" : {self.garden_property(macaddr, "lightTemp")} }}',
            }
        )

        results = await self._post_request(self._update_url, post_data)
        if not results:
            return False

        if results.get("code") == 1:
            await self.update()
            return True

        self._error_msg = (
            f"Didn't get code 1 from update API call: {results.get('msg')}"
        )
        return False

    @property
    def gardens(self):
        return list(self._data.keys())

    async def update(self) -> bool:
        if not self.is_valid_login():
            if not await self.login():
                return False

        post_data = f"userID={self._userid}"
        garden_data = await self._post_request(self._status_url, post_data)

        if not garden_data:
            return False

        if "Message" in garden_data:
            self._error_msg = f"Couldn't get data for garden: {garden_data['Message']}"
            _LOGGER.error(self._error_msg)
            return False

        new_data = {}
        for garden in garden_data:
            if "plantedName" in garden:
                garden["plantedName"] = base64.b64decode(garden["plantedName"]).decode(
                    "utf-8"
                )

            garden_id = garden.get("configID")
            garden_mac = (
                f"{garden['airGuid']}-{'' if garden_id is None else str(garden_id)}"
            )
            new_data[garden_mac] = garden

        self._data = new_data
        return True

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def throttled_update(self) -> bool:
        # Call the update method
        return await self.update()

    async def _post_request(self, url: str, post_data: str) -> Optional[Dict[str, Any]]:
        session = async_get_clientsession(self._hass)
        try:
            async with async_timeout.timeout(10):
                async with session.post(
                    url, data=post_data, headers=self._headers
                ) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            f"HTTP error {response.status} while requesting {url}"
                        )
                        return None
                    return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error requesting data from {url}: {err}")
        except json.JSONDecodeError:
            _LOGGER.error(f"Error decoding response from {url}")
        except asyncio.TimeoutError:
            _LOGGER.error(f"Timeout while requesting data from {url}")
        return None
