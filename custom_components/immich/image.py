from datetime import datetime, timedelta
import logging
from typing import Any
import random
from io import BytesIO

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_WATCHED_ALBUMS, DOMAIN, CONF_CROP_MODE, CONF_IMAGE_SELECTION_MODE,
    CONF_UPDATE_INTERVAL, CONF_UPDATE_INTERVAL_UNIT,
    DEFAULT_CROP_MODE, DEFAULT_IMAGE_SELECTION_MODE,
    DEFAULT_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_UNIT,
    CONF_CACHE_MODE, DEFAULT_CACHE_MODE
)
from .hub import ImmichHub
from .coordinator import process_images_for_slideshow

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Immich image platform."""
    hub = ImmichHub(
        host=config_entry.data[CONF_HOST], api_key=config_entry.data[CONF_API_KEY]
    )

    update_interval = config_entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    update_interval_unit = config_entry.options.get(CONF_UPDATE_INTERVAL_UNIT, DEFAULT_UPDATE_INTERVAL_UNIT)
    
    if update_interval_unit == "minutes":
        update_interval *= 60  # Convert minutes to seconds
    
    update_interval = timedelta(seconds=update_interval)
    _LOGGER.debug(f"Update interval set to {update_interval}")

    async_add_entities([ImmichImageFavorite(hass, hub, config_entry, update_interval)])

    watched_albums = config_entry.options.get(CONF_WATCHED_ALBUMS, [])
    async_add_entities(
        [
            ImmichImageAlbum(
                hass, hub, config_entry, album_id=album["id"], album_name=album["albumName"], update_interval=update_interval
            )
            for album in await hub.list_all_albums()
            if album["id"] in watched_albums
        ]
    )

class BaseImmichImage(ImageEntity):
    """Base image entity for Immich."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, hub: ImmichHub, config_entry: ConfigEntry, update_interval: timedelta) -> None:
        """Initialize the Immich image entity."""
        super().__init__(hass=hass, verify_ssl=True)
        self.hub = hub
        self.hass = hass
        self.config_entry = config_entry
        self.update_interval = update_interval
        self._current_image_bytes: bytes | None = None
        self._cached_available_asset_ids: list[str] | None = None
        self._available_asset_ids_last_updated: datetime | None = None
        self._attr_extra_state_attributes = {}
        self._unsub_interval = None

    async def async_added_to_hass(self) -> None:
        """Set up a timer to refresh the image periodically."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"Setting up image refresh timer with interval {self.update_interval}")
        self._unsub_interval = async_track_time_interval(
            self.hass, self.async_update_image, self.update_interval
        )
        # Trigger an immediate update
        await self.async_update_image()        

    async def async_will_remove_from_hass(self) -> None:
        """Cancel the timer when the entity is removed."""
        if self._unsub_interval:
            self._unsub_interval()
        await super().async_will_remove_from_hass()

    async def async_update_image(self, now: datetime | None = None) -> None:
        """Update the image."""
        _LOGGER.debug(f"Updating image at {datetime.now()}")
        await self._load_and_cache_next_image()
        self._attr_image_last_updated = datetime.now()
        self.async_write_ha_state()
        # Force Home Assistant to request the new image
        await self.async_update_ha_state()

    async def async_image(self) -> bytes | None:
        """Return bytes of image."""
        if self._current_image_bytes is None:
            await self._load_and_cache_next_image()
        return self._current_image_bytes

    async def _refresh_available_asset_ids(self) -> list[str] | None:
        """Refresh the list of available asset IDs."""
        raise NotImplementedError

    async def _get_next_asset_ids(self) -> list[str] | None:
        """Get the asset ids of the next images we want to display."""
        if (
            self._cached_available_asset_ids is None
            or self._available_asset_ids_last_updated is None
            or (datetime.now() - self._available_asset_ids_last_updated) > timedelta(hours=1)
        ):
            self._cached_available_asset_ids = await self._refresh_available_asset_ids()
            self._available_asset_ids_last_updated = datetime.now()

        if not self._cached_available_asset_ids:
            _LOGGER.error("No assets are available")
            return None

        image_selection_mode = self.config_entry.options.get(CONF_IMAGE_SELECTION_MODE, DEFAULT_IMAGE_SELECTION_MODE)
        crop_mode = self.config_entry.options.get(CONF_CROP_MODE, DEFAULT_CROP_MODE)

        num_images = 2 if crop_mode == "Combine images" else 1

        if image_selection_mode == "Random":
            return random.sample(self._cached_available_asset_ids, num_images)
        else:  # Sequential
            start_index = self._attr_extra_state_attributes.get("last_index", -1) + 1
            selected_ids = self._cached_available_asset_ids[start_index:start_index + num_images]
            if len(selected_ids) < num_images:
                selected_ids += self._cached_available_asset_ids[:num_images - len(selected_ids)]
            self._attr_extra_state_attributes["last_index"] = (start_index + num_images - 1) % len(self._cached_available_asset_ids)
            return selected_ids

    async def _load_and_cache_next_image(self) -> None:
        """Download, process, and cache the image."""
        asset_ids = await self._get_next_asset_ids()
        _LOGGER.debug(f"Got asset IDs: {asset_ids}")
        if not asset_ids:
            _LOGGER.warning("No asset IDs available")
            return

        asset_bytes_list = []
        for asset_id in asset_ids:
            asset_bytes = await self.hub.download_asset(asset_id)
            if asset_bytes:
                asset_bytes_list.append(asset_bytes)
            else:
                _LOGGER.warning(f"Failed to download asset with ID: {asset_id}")

        if not asset_bytes_list:
            _LOGGER.error("Failed to download any images")
            return

        _LOGGER.debug(f"Processing {len(asset_bytes_list)} images")
        processed_image, is_combined = process_images_for_slideshow(
            asset_bytes_list, 
            2048, 
            1536, 
            self.config_entry.options.get(CONF_CROP_MODE, DEFAULT_CROP_MODE),
            self.config_entry.options.get(CONF_IMAGE_SELECTION_MODE, DEFAULT_IMAGE_SELECTION_MODE)
        )
        
        if processed_image is None:
            _LOGGER.info("No image to display at this time (waiting for another portrait image)")
            return

        # Convert to RGB if the image is in RGBA mode
        if processed_image.mode == 'RGBA':
            processed_image = processed_image.convert('RGB')        

        with BytesIO() as output:
            processed_image.save(output, format="JPEG", quality=95, optimize=True)
            self._current_image_bytes = output.getvalue()

        _LOGGER.debug(f"Image updated, size: {len(self._current_image_bytes)} bytes, Combined: {is_combined}")
        self._attr_image_last_updated = datetime.now()

class ImmichImageFavorite(BaseImmichImage):
    """Image entity for Immich that displays a random image from the user's favorites."""

    def __init__(self, hass: HomeAssistant, hub: ImmichHub, config_entry: ConfigEntry, update_interval: timedelta) -> None:
        """Initialize the Immich image entity."""
        super().__init__(hass, hub, config_entry, update_interval)
        self._attr_unique_id = f"{config_entry.entry_id}_favorite_image"
        self._attr_name = "Immich: Random favorite image"

    async def _refresh_available_asset_ids(self) -> list[str] | None:
        """Refresh the list of available asset IDs."""
        return [image["id"] for image in await self.hub.list_favorite_images()]

class ImmichImageAlbum(BaseImmichImage):
    """Image entity for Immich that displays a random image from a specific album."""

    def __init__(self, hass: HomeAssistant, hub: ImmichHub, config_entry: ConfigEntry, album_id: str, album_name: str, update_interval: timedelta) -> None:
        """Initialize the Immich image entity."""
        super().__init__(hass, hub, config_entry, update_interval)
        self._album_id = album_id
        self._attr_unique_id = f"{config_entry.entry_id}_{album_id}"
        self._attr_name = f"Immich: {album_name}"
        hub.initialize_asset_cache(hass=self.hass, config_entry=self.config_entry)

    async def _refresh_available_asset_ids(self) -> list[str] | None:
        """Refresh the list of available asset IDs."""
        album_assets = [image["id"] for image in await self.hub.list_album_images(self._album_id)]
        await self.hub.cache_album_assets(album_assets=album_assets)
        
        return album_assets #[image["id"] for image in await self.hub.list_album_images(self._album_id)]
