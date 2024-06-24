from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import DOMAIN, CONF_API_KEY

class AeroGardenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}

        if user_input is not None:
            try:
                # Validate the API key by attempting to connect
                await self.validate_api_key(user_input[CONF_API_KEY])
                
                # If validation is successful, create the config entry
                return self.async_create_entry(
                    title="AeroGarden",
                    data=user_input,
                )
            except Exception:  # Replace with specific exceptions based on the API
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def validate_api_key(self, api_key: str) -> None:
        # Implement API key validation logic here
        # This should attempt to connect to the AeroGarden API
        # and raise an exception if it fails
        pass