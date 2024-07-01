import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .api import AerogardenAPI
from .const import DEFAULT_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup the aerogarden platform"""

    """Set up Aerogarden from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    # Use the username and password to set up aerogarden

    # If the setup is successful:
    hass.data[DOMAIN][entry.entry_id] = {
        "email": email,
        "password": password,
    }

    ag = AerogardenAPI(hass, email, password, DEFAULT_HOST)
    await ag.login()
    if not ag.is_valid_login():
        _LOGGER.error("Invalid login: %s" % ag.error)
        return False

    _ = await ag.update()

    # store the aerogarden API object into hass data system
    hass.data[DOMAIN] = ag
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Done adding components.")
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
