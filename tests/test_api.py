from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
import pytest

from custom_components.aerogarden.api import AerogardenAPI


@pytest.fixture
def hass():
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def api(hass):
    return AerogardenAPI(hass, "test@example.com", "password", "http://example.com")


@pytest.mark.asyncio
async def test_login_success(api):
    with patch(
        "custom_components.aerogarden.api.AerogardenAPI._post_request"
    ) as mock_post:
        mock_post.return_value = {"code": 123}
        result = await api.login()
        assert result is True
        assert api.is_valid_login() is True


@pytest.mark.asyncio
async def test_login_failure(api):
    with patch(
        "custom_components.aerogarden.api.AerogardenAPI._post_request"
    ) as mock_post:
        mock_post.return_value = {"code": 0}
        result = await api.login()
        assert result is False
        assert api.is_valid_login() is False
        assert api.error is not None


@pytest.mark.asyncio
async def test_update_success(api):
    api._userid = "123"  # Simulate successful login
    mock_garden_data = [
        {
            "airGuid": "AA:BB:CC:DD:EE:FF",
            "configID": 1,
            "plantedName": "UGxhbnQgTmFtZQ==",  # Base64 encoded "Plant Name"
            "chooseGarden": 0,
            "lightTemp": 1,
        }
    ]
    with patch(
        "custom_components.aerogarden.api.AerogardenAPI._post_request"
    ) as mock_post:
        mock_post.return_value = mock_garden_data
        result = await api.update()
        assert result is True
        assert "AA:BB:CC:DD:EE:FF-1" in api.gardens
        assert api.garden_name("AA:BB:CC:DD:EE:FF-1") == "Plant Name_left"


@pytest.mark.asyncio
async def test_update_failure(api):
    api._userid = "123"  # Simulate successful login
    with patch(
        "custom_components.aerogarden.api.AerogardenAPI._post_request"
    ) as mock_post:
        mock_post.return_value = {"Message": "Error"}
        result = await api.update()
        assert result is False
        assert api.error is not None


@pytest.mark.asyncio
async def test_light_toggle_success(api):
    api._userid = "123"  # Simulate successful login
    api._data = {"AA:BB:CC:DD:EE:FF-1": {"chooseGarden": 0, "lightTemp": 1}}
    with (
        patch(
            "custom_components.aerogarden.api.AerogardenAPI._post_request"
        ) as mock_post,
        patch("custom_components.aerogarden.api.AerogardenAPI.update") as mock_update,
    ):
        mock_post.return_value = {"code": 1}
        mock_update.return_value = True
        result = await api.light_toggle("AA:BB:CC:DD:EE:FF-1")
        assert result is True
        assert mock_post.call_count == 1
        assert mock_update.call_count == 1


@pytest.mark.asyncio
async def test_light_toggle_failure(api):
    api._userid = "123"  # Simulate successful login
    api._data = {"AA:BB:CC:DD:EE:FF-1": {"chooseGarden": 0, "lightTemp": 1}}
    with patch(
        "custom_components.aerogarden.api.AerogardenAPI._post_request"
    ) as mock_post:
        mock_post.return_value = {"code": 0, "msg": "Error"}
        result = await api.light_toggle("AA:BB:CC:DD:EE:FF-1")
        assert result is False
        assert api.error is not None


def test_garden_property(api):
    api._data = {
        "AA:BB:CC:DD:EE:FF-1": {
            "plantedName": "Test Plant",
            "chooseGarden": 0,
            "lightTemp": 1,
        }
    }
    assert api.garden_property("AA:BB:CC:DD:EE:FF-1", "plantedName") == "Test Plant"
    assert api.garden_property("AA:BB:CC:DD:EE:FF-1", "chooseGarden") == 0
    assert api.garden_property("AA:BB:CC:DD:EE:FF-1", "nonexistent") is None


@pytest.mark.asyncio
async def test_update_throttle(api):
    api._userid = "123"  # Simulate successful login
    with (
        patch(
            "custom_components.aerogarden.api.AerogardenAPI._post_request"
        ) as mock_post,
        patch("custom_components.aerogarden.api.MIN_TIME_BETWEEN_UPDATES", new=1),
    ):
        mock_post.return_value = [{"airGuid": "AA:BB:CC:DD:EE:FF", "configID": 1}]

        # First call should update
        result1 = await api.throttled_update()
        assert result1 is True
        assert mock_post.call_count == 1

        # Second immediate call should not update due to throttle
        result2 = await api.throttled_update()
        assert result2 is None
        assert mock_post.call_count == 1

        # Call with no_throttle should update
        result3 = await api.update()
        assert result3 is True
        assert mock_post.call_count == 2
