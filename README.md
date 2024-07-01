# homeassistant-aerogarden
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)


[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/jacobdonenfeld/homeassistant-aerogarden/master.svg)](https://results.pre-commit.ci/latest/github/jacobdonenfeld/homeassistant-aerogarden/master)
[![codecov](https://codecov.io/github/jacobdonenfeld/homeassistant-aerogarden/branch/master/graph/badge.svg?token=WTX0LQ6JGE)](https://codecov.io/github/jacobdonenfeld/homeassistant-aerogarden)


This is a custom component for [Home Assistant](http://home-assistant.io) that adds support for the Miracle Grow [AeroGarden](http://www.aerogarden.com) Wifi hydroponic gardens.


## Background
This was developed without collaboration with AeroGarden, and as of publication, there is no documented public API. This implementation was forked from that of ksheumaker after it was declared unmaintained, who in turn took inspiration and code from the code in this [forum post by epotex](https://community.home-assistant.io/t/first-timer-trying-to-convert-a-working-script-to-create-support-for-a-new-platform).

Currently, the code is setup to query the AeroGarden servers every 30 seconds.

## Tested Models

* Harvest Wifi

(Other models are expected to work, since this queries AeroGarden's cloud service rather than the garden directly. Please confirm success in an issue if you use another model, so that the documentation may be updated.)

## Installation

### HACS
This integration is a default HACS integration. Simply by searching aerogarden in HACS integrations should allow one to find and install.

### Manual (Testing custom changes)
Copy `custom_components/aerogarden` into your Home Assistant `config` directory.
Your directory structure should look like this:
```
   config/custom_components/aerogarden/__init__.py
   config/custom_components/aerogarden/api.py
   config/custom_components/aerogarden/binary_sensor.py
   config/custom_components/aerogarden/sensor.py
   config/custom_components/aerogarden/light.py
```

### Post installation steps

Note: Beta release has an automatic setup flow in process.

- Restart HA
- Add the following entry to `configuration.yaml`:
```yaml
aerogarden:
    username: [EMAIL]
    password: [PASSWORD]
```
- Restart HA final time

## Data available
The component supports multiple gardens, and multiple sensors will be created for each garden.  [GARDEN NAME] will be replaced by the garden name in the AeroGarden app.

### Light
* light.aerogarden_[GARDEN NAME]_light

### Binary Sensors (on/off)
* binary_sensor.aerogarden_[GARDEN NAME]_pump
* binary_sensor.aerogarden_[GARDEN NAME]_need_nutrients
* binary_sensor.aerogarden_[GARDEN NAME]_need_water

### Sensors
* sensor.aerogarden_[GARDEN NAME]_nutrient
* sensor.aerogarden_[GARDEN NAME]_planted

### Sample screenshot
![Screen Shot](https://raw.githubusercontent.com/jacobdonenfeld/homeassistant-aerogarden/master/screen_shot.png)

## TODO
1. Investigate the ease of turning on/off the light. See if it can be dimmed with more control.
2. Full integration overhaul (See aerogarden-v2 branch)
   1. integration flow to setup
   2. Create an aerogarden device
   3. All calls are done async
