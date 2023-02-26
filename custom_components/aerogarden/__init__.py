import base64
import json
import logging
import re
import urllib
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
import requests
import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.discovery import load_platform
from homeassistant.util import Throttle
from requests import RequestException

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aerogarden"
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


# cleanPassword assumes there is one or zero instances of password in the text
# replaces the password with <password>
def cleanPassword(text, password):
    passwordLen = len(password)
    if passwordLen == 0:
        return text
    replaceText = "<password>"
    for i in range(len(text) + 1 - passwordLen):
        if text[i : (i + passwordLen)] == password:
            restOfString = text[(i + passwordLen) :]
            text = text[:i] + replaceText + restOfString
            break
    return text


def postAndHandle(url, post_data, headers):
    try:
        r = requests.post(url, data=post_data, headers=headers)
    except RequestException as ex:
        _LOGGER.exception("Error communicating with aerogarden servers:\n %s", str(ex))
        return False

    try:
        response = r.json()
    except ValueError as ex:
        # Remove password before printing
        _LOGGER.exception(
            "error: Could not marshall post request to json.\nexception:\n%s",
            str(r),
            ex,
        )
        return False
    return response


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

        response = postAndHandle(url, post_data, self._headers)
        _LOGGER.debug(
            "Login URL: %s, post data: %s, headers: %s "
            % (url, cleanPassword(str(post_data), self._password), self._headers)
        )

        if not response:
            _LOGGER.exception("Issue logging into aerogarden servers.")
            return False

        userid = response["code"]
        if userid > 0:
            self._userid = str(userid)
        else:
            error_msg = "Login api call returned %s" % (response["code"])
            self._error_msg = error_msg

            _LOGGER.exception(error_msg)

    def is_valid_login(self):
        if self._userid:
            return True
        _LOGGER.debug("Could not find valid login")
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
            _LOGGER.debug(
                "light_toggle called for macaddr %s, on struct %s, but struct doesn't have addr",
                vars(self),
            )
            return None

        post_data = json.dumps(
            {
                "airGuid": macaddr,
                "chooseGarden": self.garden_property(macaddr, "chooseGarden"),
                "userID": self._userid,
                "plantConfig": '{ "lightTemp" : %d }'
                % (self.garden_property(macaddr, "lightTemp"))
                # TODO: Light Temp may not matter, check.
            }
        )
        url = self._host + self._update_url
        _LOGGER.debug(f"Sending POST data to toggle light: {post_data}")

        results = postAndHandle(url, post_data, self._headers)
        if not results:
            return False

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

        garden_data = postAndHandle(url, post_data, self._headers)
        if not garden_data:
            return False

        if "Message" in garden_data:
            error_msg = "Couldn't get data for garden (correct macaddr?): %s" % (
                garden_data["Message"]
            )
            self._error_msg = error_msg
            _LOGGER.exception(error_msg)
            return False

        for garden in garden_data:
            if "plantedName" in garden:
                garden["plantedName"] = base64.b64decode(garden["plantedName"]).decode(
                    "utf-8"
                )

            # Seems to be for multigarden config, untested, adapted from
            # https://github.com/JeremyKennedy/homeassistant-aerogarden/commit/5854477c35103d724b86490b90e286b5d74f6660
            garden_id = garden.get("configID", None)
            garden_mac = (
                garden["airGuid"] + "-" + ("" if garden_id is None else str(garden_id))
            )
            data[garden_mac] = garden

        _LOGGER.debug("Updating data {}".format(data))
        self._data = data
        return True


def setup(hass, config: dict):
    """Setup the aerogarden platform"""

    domain_config = config.get(DOMAIN)

    username = domain_config.get(CONF_USERNAME)
    password = domain_config.get(CONF_PASSWORD)

    host = domain_config.get(CONF_HOST, DEFAULT_HOST)

    ag = AerogardenAPI(username, password, host)
    if not ag.is_valid_login():
        _LOGGER.error("Invalid login: %s" % ag.error)
        return

    ag.update()

    # store the aerogarden API object into hass data system
    hass.data[DOMAIN] = ag

    load_platform(hass, "sensor", DOMAIN, {}, config)
    load_platform(hass, "binary_sensor", DOMAIN, {}, config)
    load_platform(hass, "light", DOMAIN, {}, config)
    _LOGGER.debug("Done adding components.")

    return True
