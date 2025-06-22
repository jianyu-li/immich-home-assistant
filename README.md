> [!WARNING]
> **This repository is no longer maintained.**
> 
> Support for Immich is now included as a built-in [Home Assistant integration](https://www.home-assistant.io/integrations/immich/). Please use the official integration for all future updates and support.

# Immich × Home Assistant 

A fork from [immich-home-assistant](https://github.com/outadoc/immich-home-assistant) that incorporates some of the pull requests since the development is a little stale. 

# Updates from original

### 🖼️ Crop Mode Options
Thanks to [@anon666333](https://github.com/anon666333) for their contributions!

The crop_mode option controls how images are displayed on your screen, especially when dealing with mismatched orientations. Choose the mode that best suits your display and aesthetic preferences:

🔀 Combine images
	•	Description: Pairs two portrait-oriented images side-by-side on a single canvas, centered vertically.
	•	Behavior:
	•	If two portrait images are available, they are combined into one landscape image.
	•	If only one portrait image is available, it’s held until the next portrait arrives.
	•	Falls back to a landscape image if no portrait pair is possible.
	•	Best for: Portrait-heavy albums, maximizing screen space, dynamic pairings.

✂️ Crop single image
	•	Description: Crops a single image to exactly fill the screen dimensions, possibly trimming edges.
	•	Behavior: Uses smart cropping (ImageOps.fit) to preserve center content but may cut off sides or top/bottom.
	•	Best for: Slideshows, digital frames, or dashboards where exact fit matters more than full image preservation.

📏 None
	•	Description: Resizes the image to fit the screen without cropping.
	•	Behavior: Entire image is shown using letterboxing or pillarboxing if needed.
	•	Best for: Preserving full image content, galleries, or artistic displays.

### Better Compatibility
Thanks to [@9zigen](https://github.com/9zigen) for their contributions!

The original was not compatible with file formats like HEIC, this new version uses the thumbnail preview to load the picture instead of the original photo file. 

This custom integration for Home Assistant allows you to display random pictures from your Immich instance right inside your dashboards.

# Original README

### What is Immich?

Immich is a "high performance self-hosted photo and video backup solution".  
[Find more on their website](https://immich.app).

### What is Home Assistant?

Home Assistant provides "open source home automation that puts local control and privacy first".  
[Find more on their website](https://www.home-assistant.io).

## Installation

Install this component _via_ [HACS](https://hacs.xyz).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=immich-home-assistant&category=Integration&owner=jianyu-li)

Restart Home Assistant once the integration has been installed.

## What can I do with this project?

As a suggestion, you could use this integration to create a picture frame. You can create a "pane" dashboard, and display your picture entity inside of it:

```yaml
type: panel
title: Photo frame
path: photo-frame
icon: mdi:image-frame
subview: true
cards:
  - type: picture-entity
    entity: image.immich_favorite_image
    show_state: false
    show_name: false
    aspect_ratio: "16:9"
    fit_mode: contain
```

You can then use this dashboard on a dedicated device in kiosk mode.

You could even display in onto a Nest Hub device with the [Home Assistant Cast](https://www.home-assistant.io/integrations/cast/#home-assistant-cast) feature − you can finally say goodbye to Google Photos! 🎉

```yaml
- service: cast.show_lovelace_view
  data:
    entity_id: media_player.<your-chromecast-device>
    dashboard_path: lovelace
    view_path: photo-frame
```

![A Nest Hub 2 showing a cat picture, straight from Home Assistant](assets/demo.jpg)

## How does it work?

The integration can provide multiple `image` entities, which each correspond to an album. Each entity will switch to a new random image every 5 minutes.

These entities can be displayed using standard lovelace cards − for example, the `picture`, or `picture-entity` cards.

<img src="assets/entity-card.png" width="600" alt="Example usage: a picture card showing a picture from Immich">

## Configuration

You can set up the Immich integration right from the web UI.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=immich)

You will need to enter your instance's URL and an API key. You can generate it from your Account Settings, on your Immich instance.

<img src="assets/immich-api-key.png" width="600" alt="'API Keys' section on the Immich account settings page">

### Exposing other albums

By default, only the "Favorites" album is exposed as an entity.

You can expose more albums on the integration's options page.

> [!WARNING]  
> Exposing many albums might consume a lot of resources on your Home Assistant machine, and will also increase the number of calls to your Immich instance.

<img src="assets/entity-list.png" width="600" alt="A list of four image entities provided by the Immich integration">
