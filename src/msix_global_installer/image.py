from PIL import Image
import pathlib

def scale_image(image_path, width, height) -> Image:
    """Scale an image and return it."""
    # Open the image using Pillow
    img = Image.open(image_path)
    # Resize the image to the specified width and height
    img = img.resize((width, height), Image.Resampling.BICUBIC)
    return img

def save_image(img: Image, path: pathlib.Path):
    """Save a given image"""
    img.save(path)