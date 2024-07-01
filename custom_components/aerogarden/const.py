"""Constants for the Aerogarden integration."""

from datetime import timedelta
from typing import Final

DEFAULT_HOST: Final = "https://app4.aerogarden.com"
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)
DOMAIN: Final = "aerogarden"
MANUFACTURER: Final = "Aerogarden"
UPDATE_INTERVAL: float = 30.0
