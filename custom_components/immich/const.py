"""Constants for the immich integration."""

import voluptuous as vol

DOMAIN = "immich"
CONF_WATCHED_ALBUMS = "watched_albums"

# Crop Mode Constants
CROP_MODES = ["Combine images", "Crop single image", "None"]
CONF_CROP_MODE = "crop_mode"
DEFAULT_CROP_MODE = "Combine images"

# Image Selection Constants
CONF_IMAGE_SELECTION_MODE = "image_selection_mode"
IMAGE_SELECTION_MODES = ["Random", "Sequential"]
DEFAULT_IMAGE_SELECTION_MODE = "Random"

# Update Interval Constants
CONF_UPDATE_INTERVAL = "update_interval"
CONF_UPDATE_INTERVAL_UNIT = "update_interval_unit"
DEFAULT_UPDATE_INTERVAL = 60  # in seconds
DEFAULT_UPDATE_INTERVAL_UNIT = "seconds"
UPDATE_INTERVAL_UNITS = ["seconds", "minutes"]

CONF_CACHE_MODE = "cache_mode"
DEFAULT_CACHE_MODE = False

PICTURE_TYPES = ["preview", "fullsize"]
CONF_PICTURE_TYPE = "picture_type"
DEFAULT_PICTURE_TYPE = "preview"

# Validation for update interval (min=1 second, max=24 hours)
UPDATE_INTERVAL_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=1, max=86400))
