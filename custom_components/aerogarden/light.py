import logging

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Aerogarden light platform."""
    aerogarden_api = hass.data[DOMAIN][entry.entry_id]
    lights = []

    for garden in aerogarden_api.gardens:
        lights.append(AerogardenLight(garden, aerogarden_api))

    async_add_entities(lights, True)


class AerogardenLight(LightEntity):
    """Representation of an Aerogarden light."""

    def __init__(self, macaddr, aerogarden_api, field="lightStat", label="light"):
        """Initialize the light."""
        self._aerogarden = aerogarden_api
        self._macaddr = macaddr
        self._field = field
        self._attr_name = f"{DOMAIN} {self._aerogarden.garden_property(self._macaddr, 'plantedName')} {label}"
        self._attr_unique_id = f"{self._macaddr}_{label}"
        self._attr_is_on = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Aerogarden device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._macaddr)},
            name=self._aerogarden.garden_property(self._macaddr, "plantedName"),
            manufacturer="Aerogarden",
            model="Aerogarden",  # You might want to get the actual model if available
        )

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        await self._aerogarden.light_toggle(self._macaddr)
        self._attr_is_on = True

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        await self._aerogarden.light_toggle(self._macaddr)
        self._attr_is_on = False

    async def async_update(self) -> None:
        """Fetch new state data for the light."""
        await self._aerogarden.throttled_update()
        self._attr_is_on = (
            self._aerogarden.garden_property(self._macaddr, self._field) == 1
        )
