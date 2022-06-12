import logging

import homeassistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .. import aerogarden

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["aerogarden"]


class AerogardenSensor(CoordinatorEntity, Entity):
    def __init__(
        self,
        macaddr,
        aerogarden_api,
        field,
        label=None,
        icon=None,
        unit=None,
    ):
        self._aerogarden = aerogarden_api
        self._macaddr = macaddr
        self._field = field
        self._label = label
        if not label:
            self._label = field
        self._icon = icon
        self._unit = unit

        self._garden_name = self._aerogarden.garden_name(self._macaddr)

        self._name = "%s %s" % (
            self._garden_name,
            self._label,
        )

        self._unique_id = "%s %s" % (
            self._garden_name,
            self._field,
        )
        self._state = self._aerogarden.garden_property(self._macaddr, self._field)

    @property
    def unique_id(self):
        """Return the ID of this purifier."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the garden if any."""
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return self._icon

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def unit_of_measurement(self):
        return self._unit

    def update(self):
        self._aerogarden.update()
        self._state = self._aerogarden.garden_property(self._macaddr, self._field)


async def async_setup_entry(hass, ConfigEntry, async_add_entities):
    """Setup the aerogarden platform"""

    aerogarden_api = hass.data[aerogarden.DOMAIN]

    sensors = []
    sensor_fields = {
        "plantedDay": {"label": "Planted Days", "icon": "mdi:calendar", "unit": "Days"},
        "nutriRemindDay": {
            "label": "Nutrient Days",
            "icon": "mdi:calendar-clock",
            "unit": "Days",
        },
        "pumpLevel": {
            "label": "Pump Level",
            "icon": "mdi:water-percent",
            "unit": "Fill Level",
        },
    }

    for garden in aerogarden_api.gardens:  # This may be unnecessary now
        for field in sensor_fields.keys():  # plantedDay, NitriRemindDay, pumpLever
            s = sensor_fields[field]  # Values
            sensors.append(
                AerogardenSensor(
                    garden,
                    aerogarden_api,
                    field,
                    label=s["label"],
                    icon=s["icon"],
                    unit=s["unit"],
                )
            )

    async_add_entities(sensors)
