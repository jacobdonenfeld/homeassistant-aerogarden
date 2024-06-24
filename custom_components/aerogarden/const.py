"""Constants for the Aerogarden integration."""

DOMAIN = "aerogarden"
DEFAULT_HOST = "https://app3.aerogarden.com:8443"

# Configuration
CONF_API_KEY = "api_key"  # If you decide to use an API key instead of username/password

# URLs
LOGIN_URL = "/api/Admin/Login"
STATUS_URL = "/api/CustomData/QueryUserDevice"
UPDATE_URL = "/api/Custom/UpdateDeviceConfig"

# Update interval
UPDATE_INTERVAL = 30  # seconds

# Error messages
ERROR_AUTH = "Invalid authentication"
ERROR_CONNECTION = "Connection error"

# Attributes
ATTR_LIGHT_STATE = "light_state"
ATTR_PUMP_STATE = "pump_state"
ATTR_WATER_LEVEL = "water_level"
ATTR_NUTRIENT_LEVEL = "nutrient_level"
ATTR_PLANTED_DATE = "planted_date"
ATTR_PLANT_TYPE = "plant_type"
ATTR_GROW_LIGHT_TIME = "grow_light_time"

# States
STATE_ON = "on"
STATE_OFF = "off"
STATE_DIMMED = "dimmed"

# Light states
LIGHT_STATE_BRIGHT = "bright"
LIGHT_STATE_DIMMED = "dimmed"
LIGHT_STATE_OFF = "off"

# Device classes
DEVICE_CLASS_LIGHT = "light"
DEVICE_CLASS_PUMP = "switch"
DEVICE_CLASS_WATER_LEVEL = "moisture"
DEVICE_CLASS_NUTRIENT_LEVEL = "nutrient"