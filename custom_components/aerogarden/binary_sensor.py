import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_FIELDS = {
    "pumpStat": {
        "label": "pump",
        "icon": "mdi:water-pump",
        "device_class": BinarySensorDeviceClass.RUNNING,
    },
    "nutriStatus": {
        "label": "Needs nutrients",
        "icon": "mdi:cup-water",
        "device_class": BinarySensorDeviceClass.PROBLEM,
    },
    "pumpHydro": {
        "label": "Needs water",
        "icon": "mdi:water",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Aerogarden binary sensor platform."""
    aerogarden_api = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    for garden in aerogarden_api.gardens:
        for field, attributes in SENSOR_FIELDS.items():
            sensors.append(
                AerogardenBinarySensor(
                    garden,
                    aerogarden_api,
                    field,
                    attributes["label"],
                    attributes["icon"],
                    attributes["device_class"],
                )
            )

    async_add_entities(sensors, True)


class AerogardenBinarySensor(BinarySensorEntity):
    """Representation of an Aerogarden binary sensor."""

    def __init__(self, macaddr, aerogarden_api, field, label, icon, device_class):
        """Initialize the binary sensor."""
        self._aerogarden = aerogarden_api
        self._macaddr = macaddr
        self._field = field
        self._attr_name = f"{self._aerogarden.garden_name(self._macaddr)} {label}"
        self._attr_unique_id = f"{self._macaddr}_{label}"
        self._attr_icon = icon
        self._attr_device_class = device_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Aerogarden device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._macaddr)},
            name=self._aerogarden.garden_name(self._macaddr),
            manufacturer="Aerogarden",
            model="Aerogarden",  # You might want to get the actual model if available
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._aerogarden.garden_property(self._macaddr, self._field) == 1

    async def async_update(self) -> None:
        """Fetch new state data for the binary sensor."""
        await self._aerogarden.throttled_update()
