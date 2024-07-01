from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.aerogarden.const import DOMAIN


@dataclass
class MockConfigEntry:
    domain: str
    data: dict
    unique_id: str | None = None

    def add_to_hass(self, hass):
        """Mock add config to hass."""
        hass.config_entries._entries.append(self)


@pytest.fixture
def hass():
    """Fixture to provide a test instance of Home Assistant."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.flow.async_init = MagicMock()
    hass.config_entries.flow.async_configure = MagicMock()
    hass.config_entries._entries = []
    return hass


@pytest.fixture(autouse=True)
def mock_api():
    with patch("custom_components.aerogarden.api.AerogardenAPI") as mock_api:
        mock_api_instance = mock_api.return_value
        mock_api_instance.login.return_value = True
        yield mock_api_instance


@pytest.mark.asyncio
async def test_user_form(hass):
    """Test we get the user form."""
    result = {"type": data_entry_flow.RESULT_TYPE_FORM, "errors": {}}
    hass.config_entries.flow.async_init.return_value = result

    flow_result = hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert flow_result == result


@pytest.mark.asyncio
async def test_user_form_invalid_auth(hass, mock_api):
    """Test we handle invalid auth."""
    mock_api.login.return_value = False

    result = {
        "type": data_entry_flow.RESULT_TYPE_FORM,
        "errors": {"base": "invalid_auth"},
    }
    hass.config_entries.flow.async_configure.return_value = result

    flow_result = hass.config_entries.flow.async_configure(
        "test-flow-id",
        {CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
    )

    assert flow_result == result


@pytest.mark.asyncio
async def test_user_form_cannot_connect(hass, mock_api):
    """Test we handle cannot connect error."""
    mock_api.login.side_effect = ConnectionError

    result = {"type": data_entry_flow.RESULT_TYPE_FORM, "errors": {"base": "unknown"}}
    hass.config_entries.flow.async_configure.return_value = result

    flow_result = hass.config_entries.flow.async_configure(
        "test-flow-id",
        {CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
    )

    assert flow_result == result


@pytest.mark.asyncio
async def test_user_form_valid_credentials(hass, mock_api):
    """Test we can create an entry with valid credentials."""
    result = {
        "type": data_entry_flow.RESULT_TYPE_CREATE_ENTRY,
        "title": "Aerogarden (test-username)",
        "data": {
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "test-password",
        },
    }
    hass.config_entries.flow.async_configure.return_value = result

    flow_result = hass.config_entries.flow.async_configure(
        "test-flow-id",
        {CONF_USERNAME: "test-username", CONF_PASSWORD: "test-password"},
    )

    assert flow_result == result


@pytest.mark.asyncio
async def test_user_form_unique_id(hass, mock_api):
    """Test we only allow a single config flow for a given username."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="existing-username",
        data={CONF_USERNAME: "existing-username", CONF_PASSWORD: "existing-password"},
    ).add_to_hass(hass)

    # Simulate the initial form
    init_result = {"type": data_entry_flow.RESULT_TYPE_FORM, "errors": {}}
    hass.config_entries.flow.async_init.return_value = init_result

    flow_result = hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert flow_result == init_result

    # Simulate the configuration attempt with existing username
    abort_result = {
        "type": data_entry_flow.RESULT_TYPE_ABORT,
        "reason": "already_configured",
    }
    hass.config_entries.flow.async_configure.return_value = abort_result

    flow_result = hass.config_entries.flow.async_configure(
        "test-flow-id",
        {CONF_USERNAME: "existing-username", CONF_PASSWORD: "test-password"},
    )

    assert flow_result == abort_result
