import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import ConfigEntryNotReady

from .api import AerogardenAPI
from .const import DEFAULT_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class AerogardenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        errors = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            ag = AerogardenAPI(self.hass, email, password, DEFAULT_HOST)
            try:
                is_valid = await ag.login()
                if is_valid:
                    # Check if this email is already configured
                    await self.async_set_unique_id(email)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Aerogarden ({email})", data=user_input
                    )
                else:
                    errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.error("Unexpected error occurred: %s", str(e))
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up Aerogarden from a config entry."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    ag = AerogardenAPI(hass, email, password, DEFAULT_HOST)

    try:
        is_valid = await ag.login()
        if not is_valid:
            raise ConfigEntryNotReady("Invalid login credentials")

        await ag.update()
    except Exception as e:
        _LOGGER.error("Error setting up Aerogarden integration: %s", str(e))
        raise ConfigEntryNotReady from e

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ag

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor", "light"]
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "binary_sensor", "light"]
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
