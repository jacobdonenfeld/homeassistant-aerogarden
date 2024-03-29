import logging

from homeassistant.components.light import LightEntity

from .. import aerogarden

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["aerogarden"]


class AerogardenLight(LightEntity):
    def __init__(self, macaddr, aerogarden_api, field="lightStat", label="light"):
        self._aerogarden = aerogarden_api
        self._macaddr = macaddr
        self._field = field
        self._label = label
        if not label:
            self._label = field

        self._garden_name = self._aerogarden.garden_property(
            self._macaddr, "plantedName"
        )

        self._name = "%s %s %s" % (
            aerogarden.DOMAIN,
            self._garden_name,
            self._label,
        )
        self._attr_unique_id = self._macaddr + self._label
        self._state = self._aerogarden.garden_property(self._macaddr, self._field)

        _LOGGER.debug("Initialized garden lightStat:\n%s", vars(self))

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        if self._state == 1:
            return True
        return False

    def turn_on(self, **kwargs):
        self._aerogarden.light_toggle(self._macaddr)
        self._state = 1

    def turn_off(self, **kwargs):
        self._aerogarden.light_toggle(self._macaddr)
        self._state = 0

    def update(self):
        self._aerogarden.update()
        self._state = self._aerogarden.garden_property(self._macaddr, self._field)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Aerogarden platform"""

    ag = hass.data[aerogarden.DOMAIN]

    lights = []

    for garden in ag.gardens:
        lights.append(AerogardenLight(garden, ag))

    add_devices(lights)
