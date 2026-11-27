"""Safe profile-picture handling: verify it is really an image, crop square, resize, re-encode as PNG."""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 3 * 1024 * 1024
SIZE = 256
Image.MAX_IMAGE_PIXELS = 25_000_000   # refuse decompression bombs


class AvatarError(ValueError):
    pass


def process(data: bytes) -> bytes:
    if not data:
        raise AvatarError("No image received.")
    if len(data) > MAX_BYTES:
        raise AvatarError("Image is too large (max 3 MB).")
    try:
        probe = Image.open(BytesIO(data)); probe.verify()           # checks the file really is an image
        img = Image.open(BytesIO(data))
        if img.format not in ("PNG", "JPEG", "WEBP", "GIF"):
            raise AvatarError("Please upload a PNG, JPG, WEBP or GIF image.")
        img = ImageOps.exif_transpose(img).convert("RGBA")           # fix phone-photo rotation, drop metadata
    except AvatarError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError):
        raise AvatarError("That file is not a valid image.")
    img = ImageOps.fit(img, (SIZE, SIZE), Image.LANCZOS)            # centre-crop to a square
    out = BytesIO(); img.save(out, "PNG", optimize=True)
    return out.getvalue()
