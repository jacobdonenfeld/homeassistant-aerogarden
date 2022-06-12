import asyncio
import base64
import logging
import urllib
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import Throttle
from requests import RequestException

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aerogarden"
SENSOR_PREFIX = "aerogarden"
DEFAULT_HOST = "https://app3.aerogarden.com:8443"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class AerogardenAPI:
    def __init__(self, username, password, host=None):
        self._username = urllib.parse.quote(username)
        self._password = urllib.parse.quote(password)
        self._host = host
        self._userid = None
        self._error_msg = None
        self._data = None
        self.gardens = []

        self._login_url = "/api/Admin/Login"
        self._status_url = "/api/CustomData/QueryUserDevice"
        self._update_url = "/api/Custom/UpdateDeviceConfig"

        self._headers = {
            "User-Agent": "HA-Aerogarden/0.1",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        self.login()

    @property
    def error(self):
        return self._error_msg

    def login(self):

        post_data = "mail=" + self._username + "&userPwd=" + self._password
        url = self._host + self._login_url

        try:
            r = requests.post(url, data=post_data, headers=self._headers)
        except RequestException:
            _LOGGER.exception("Error communicating with aerogarden servers")
            return False

        response = r.json()

        userid = response["code"]
        if userid > 0:
            self._userid = str(userid)
        else:
            self._error_msg = "Login api call returned %s" % (response["code"])

    def is_valid_login(self):
        if self._userid:
            return True
        return False

    def garden_name(self, macaddr):
        multi_garden = self.garden_property(macaddr, "chooseGarden")
        if not multi_garden:
            return self.garden_property(macaddr, "plantedName")
        multi_garden_label = "left" if multi_garden == 0 else "right"
        return self.garden_property(macaddr, "plantedName") + "_" + multi_garden_label

    def garden_property(self, macaddr, field):

        if macaddr not in self._data:
            return None

        if field not in self._data[macaddr]:
            return None

        return self._data[macaddr].get(field, None)

    def light_toggle(self, macaddr):
        """light_toggle:
        Toggles between Bright, Dimmed, and Off.
        I couldn't find any way to set a specific state, it just cycles between the three.
        """
        if macaddr not in self._data:
            return None

        post_data = {
            "airGuid": macaddr,
            "chooseGarden": self.garden_property(macaddr, "chooseGarden"),
            "userID": self._userid,
            "plantConfig": '{ "lightTemp" : %d }'
            % (self.garden_property(macaddr, "lightTemp"))
            # TODO: Light Temp may not matter, check.
        }
        url = self._host + self._update_url
        _LOGGER.debug(f"Sending POST data to toggle light: {post_data}")

        try:
            r = requests.post(url, data=post_data, headers=self._headers)
        except RequestException:
            _LOGGER.exception("Error communicating with aerogarden servers")
            return False

        results = r.json()

        if "code" in results:
            if results["code"] == 1:
                return True

        self._error_msg = "Didn't get code 1 from update API call: %s" % (
            results["msg"]
        )
        self.update(no_throttle=True)

        return False

    @property
    def gardens(self):
        return self._data.keys()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        data = {}
        if not self.is_valid_login():
            return

        url = self._host + self._status_url
        post_data = "userID=" + self._userid

        try:
            r = requests.post(url, data=post_data, headers=self._headers)
        except RequestException:
            _LOGGER.exception("Error communicating with aerogarden servers")
            return False

        garden_data = r.json()

        if "Message" in garden_data:
            self._error_msg = "Couldn't get data for garden (correct macaddr?): %s" % (
                garden_data["Message"]
            )
            return False

        for garden in garden_data:
            if "plantedName" in garden:
                garden["plantedName"] = base64.b64decode(garden["plantedName"]).decode(
                    "utf-8"
                )

            # Seems to be for multigarden config, untested, adapted from
            # https://github.com/JeremyKennedy/homeassistant-aerogarden/commit/5854477c35103d724b86490b90e286b5d74f6660
            id = garden.get("configID", None)
            garden_mac = garden["airGuid"] + "-" + ("" if id is None else str(id))
            data[garden_mac] = garden

        _LOGGER.debug("Updating data {}".format(data))
        self._data = data
        self.gardens = self._data.keys()
        return True


def setup(hass, config: dict):
    """Setup the aerogarden platform"""
    _LOGGER.debug("Starting setup.")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries) -> bool:
    _LOGGER.debug("Starting async setup.")
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    host = entry.data.get(CONF_HOST, DEFAULT_HOST)

    _LOGGER.info("Initializing the Aerogarden API")

    ag = await hass.async_add_executor_job(AerogardenAPI, username, password, host)
    _LOGGER.info("Connected to Aerogarden API")

    if not ag.is_valid_login():
        _LOGGER.error("Invalid login: %s" % (ag.error))
        return

    async def async_update_data():
        """Fetch data from IOCare API"""
        try:
            ag_update_data = await hass.async_add_executor_job(ag.update())
            return ag_update_data
        except Exception as e:
            raise UpdateFailed(
                f"Error occured while fetching data from Aerogarden servers: {e}"
            )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="aerogarden_coordinator",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    # store the aerogarden coordinator into hass data system
    hass.data[DOMAIN] = coordinator

    await coordinator.async_config_entry_first_refresh()

    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(
            entry, "sensor", DOMAIN, {}, entry.data
        )
    )
    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(
            entry, "binary_sensor", DOMAIN, {}, entry.data
        )
    )
    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(
            entry, "light", DOMAIN, {}, entry.data
        )
    )

    _LOGGER.debug("Done adding components.")

    return True
