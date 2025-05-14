from PIL import Image, ImageOps
from io import BytesIO
from typing import List, Tuple
import logging

Image.MAX_IMAGE_PIXELS = None
import requests

_LOGGER = logging.getLogger(__name__)

# Global variable to store a held portrait image
held_portrait_image = None

def fetch_image_from_immich(image_url: str) -> Image.Image:
    """Fetches an image from the Immich API."""
    response = requests.get(image_url)

    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        img = ImageOps.exif_transpose(img)
        return img
    else:
        raise Exception(f"Failed to fetch image from {image_url}")

def is_portrait(image: Image.Image) -> bool:
    """Check if the image is in portrait orientation."""
    width, height = image.size
    return height > width

def correct_image_orientation(image: Image.Image) -> Image.Image:
    """Correct the image orientation based on EXIF data."""
    try:
        exif = dict(image._getexif().items())
        orientation = exif.get(274, 1)  # 274 is the EXIF tag for orientation
        
        if orientation == 1:
            return image
        elif orientation == 2:
            return ImageOps.mirror(image)
        elif orientation == 3:
            return image.rotate(180, expand=True)
        elif orientation == 4:
            return ImageOps.mirror(image.rotate(180, expand=True))
        elif orientation == 5:
            return ImageOps.mirror(image.rotate(270, expand=True))
        elif orientation == 6:
            return image.rotate(270, expand=True)
        elif orientation == 7:
            return ImageOps.mirror(image.rotate(90, expand=True))
        elif orientation == 8:
            return image.rotate(90, expand=True)
        else:
            return image
    except (AttributeError, KeyError, IndexError, TypeError):
        # Cases: image don't have getexif
        _LOGGER.warning("EXIF data not available or incomplete. Using original image orientation.")
        return image

def combine_portrait_images(images: List[Image.Image], width: int, height: int) -> Image.Image:
    """Combines two portrait images side-by-side into a single image, vertically centered."""
    assert len(images) >= 2, "This function expects at least two images"
    
    # Resize images to fit within half the width and full height
    resized_images = [ImageOps.contain(img, (width // 2, height), Image.Resampling.LANCZOS) for img in images[:2]]

    combined_image = Image.new('RGB', (width, height))

    for i, img in enumerate(resized_images):
        # Calculate vertical offset to center the image
        y_offset = (height - img.height) // 2
        combined_image.paste(img, (i * (width // 2), y_offset))

    return combined_image

def process_single_image(image: Image.Image, width: int, height: int) -> Image.Image:
    """Process a single image, ensuring it's not cut off."""
    return ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)

def process_images_for_slideshow(
    image_bytes_list: List[bytes], 
    width: int, 
    height: int, 
    crop_mode: str = "Combine images",
    image_selection_mode: str = "Random"
) -> Tuple[Image.Image, bool]:
    """
    Processes images for the slideshow, applying crop or combining as needed.
    Returns a tuple of (processed_image, is_combined).
    """
    global held_portrait_image
    
    images = [correct_image_orientation(Image.open(BytesIO(image_bytes))) for image_bytes in image_bytes_list]
    
    _LOGGER.debug(f"Processing {len(images)} images. Crop mode: {crop_mode}, Selection mode: {image_selection_mode}")
    
    for i, img in enumerate(images):
        _LOGGER.debug(f"Image {i+1}: Size={img.size}, Mode={img.mode}, Format={img.format}, Orientation={'Portrait' if is_portrait(img) else 'Landscape'}")

    if crop_mode == "Combine images":
        portrait_images = [img for img in images if is_portrait(img)]
        
        if held_portrait_image:
            portrait_images.insert(0, held_portrait_image)
        
        if len(portrait_images) >= 2:
            held_portrait_image = None
            return combine_portrait_images(portrait_images[:2], width, height), True
        elif len(portrait_images) == 1:
            held_portrait_image = portrait_images[0]
            landscape_images = [img for img in images if not is_portrait(img)]
            if landscape_images:
                return process_single_image(landscape_images[0], width, height), False
            else:
                # If no landscape image is available, return None to indicate no image should be displayed
                return None, False
        else:
            # Only landscape images available
            return process_single_image(images[0], width, height), False
    elif crop_mode == "Crop single image":
        return ImageOps.fit(images[0], (width, height), Image.Resampling.LANCZOS), False
    else:  # "None" mode
        return process_single_image(images[0], width, height), False
