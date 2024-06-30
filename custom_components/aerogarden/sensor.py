import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_FIELDS = {
    "plantedDay": {"label": "Planted Days", "icon": "mdi:calendar", "unit": "Days"},
    "nutriRemindDay": {
        "label": "Nutrient Days",
        "icon": "mdi:calendar-clock",
        "unit": "Days",
    },
    "pumpLevel": {
        "label": "pump_level",
        "icon": "mdi:water-percent",
        "unit": "Fill Level",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Aerogarden sensor platform."""
    aerogarden_api = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    for garden in aerogarden_api.gardens:
        for field, attributes in SENSOR_FIELDS.items():
            sensors.append(
                AerogardenSensor(
                    garden,
                    aerogarden_api,
                    field,
                    attributes["label"],
                    attributes["icon"],
                    attributes["unit"],
                )
            )

    async_add_entities(sensors, True)


class AerogardenSensor(SensorEntity):
    """Representation of an Aerogarden sensor."""

    def __init__(self, macaddr, aerogarden_api, field, label, icon, unit):
        """Initialize the sensor."""
