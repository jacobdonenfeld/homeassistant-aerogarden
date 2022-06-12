"""Config flow of our component"""
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback

from .. import aerogarden

_LOGGER = logging.getLogger(__name__)
DOMAIN = "aerogarden"
SENSOR_PREFIX = "aerogarden"
DEFAULT_HOST = "https://app3.aerogarden.com:8443"


class AerogardenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle our config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize Aerogarden configuration flow"""
        self.schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
            }
        )

        self._username = None
        self._password = None

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if not user_input:
            return self._show_form()

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        return await self._async_iocare_login()

    async def _async_aerogarden_login(self):

        errors = {}

        try:
            client = await self.hass.async_add_executor_job(
                aerogarden.AerogardenAPI, self._username, self._password
            )
            await self.hass.async_add_executor_job(client.login)
            logged_in = await self.hass.async_add_executor_job(client.is_valid_login)
            if not logged_in:
                raise  # TODO: What to raise

        except Exception:
            _LOGGER.error("Unable to connect to Aerogarden: Failed to Log In")
            errors = {"base": "auth_error"}

        if errors:
            return self._show_form(errors=errors)

        return await self._async_create_entry()

    async def _async_create_entry(self):
        """Create the config entry."""
        config_data = {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
        }

        return self.async_create_entry(title="Aerogarden", data=config_data)

    @callback
    def _show_form(self, errors=None):
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=self.schema,
            errors=errors if errors else {},
        )
