import logging

from homeassistant.helpers.entity import Entity

from .. import aerogarden

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["aerogarden"]


class AerogardenSensor(Entity):
    def __init__(
        self, macaddr, aerogarden_api, field, label=None, icon=None, unit=None
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
        self._attr_unique_id = self._macaddr + self._label

        self._state = self._aerogarden.garden_property(self._macaddr, self._field)

        _LOGGER.debug("Initialized garden sensor %s:\n%s", field, vars(self))

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return self._icon

    @property
    def unit_of_measurement(self):
        return self._unit

    def update(self):
        self._aerogarden.update()
        self._state = self._aerogarden.garden_property(self._macaddr, self._field)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the aerogarden platform"""

    ag = hass.data[aerogarden.DOMAIN]

    sensors = []
    sensor_fields = {
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

    for garden in ag.gardens:
        for field in sensor_fields.keys():
            s = sensor_fields[field]
            sensors.append(
                AerogardenSensor(
                    garden, ag, field, label=s["label"], icon=s["icon"], unit=s["unit"]
                )
            )

    add_entities(sensors)
