import base64
import logging
import urllib
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from requests import RequestException

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aerogarden"
SENSOR_PREFIX = "aerogarden"
DATA_AEROGARDEN = "AEROGARDEN"
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

        return

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
            # id = garden.get("configID", None)
            garden_mac = garden["airGuid"]  # + "-" + ("" if id is None else str(id))
            data[garden_mac] = garden

        self._data = data
        return True


def setup(hass, config):
    """Setup the aerogarden platform"""

    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    host = config[DOMAIN].get(CONF_HOST)

    ag = AerogardenAPI(username, password, host)
    if not ag.is_valid_login():
        _LOGGER.error("Invalid login: %s" % (ag.error))
        return

    ag.update()

    # store the Aerogarden API object into hass data system
    hass.data[DATA_AEROGARDEN] = ag

    load_platform(hass, "sensor", DOMAIN, {}, config)
    load_platform(hass, "binary_sensor", DOMAIN, {}, config)
    load_platform(hass, "light", DOMAIN, {}, config)

    return True
