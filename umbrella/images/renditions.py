"""Pillow mechanics for display copies. Only images.services calls this.

    decoded image ─► EXIF orientation ─► shrink to preview ─► 8-bit ─► WebP preview
                                                                   └─► shrink ─► WebP thumb

Browsers show 8-bit pixels only, and no TIFF. 16-bit/float microscope exports get
a percentile contrast stretch, e.g. signal in 1200–4800 of 0–65535 → 0–255.
"""

import io
from dataclasses import dataclass
from enum import Enum

import numpy as np
from PIL import Image as PILImage
from PIL import ImageOps

from images.constants import PREVIEW_MAX_PX, THUMB_MAX_PX

LANCZOS = PILImage.Resampling.LANCZOS

# Pillow modes holding more than 8 bits per pixel
HIGH_DEPTH_MODES = {"I;16", "I;16B", "I;16L", "I;16N", "I", "F"}

# Modes passed to the WebP encoder as-is
WEB_MODES = {"L", "LA", "RGB", "RGBA"}

# Modes that resample badly (nearest only), so convert before shrinking
INDEXED_MODES = {"1", "P"}

# Ignore the darkest/brightest 0.5% (dead and hot pixels) when picking the window
STRETCH_PERCENTILES = (0.5, 99.5)

# Every 4th pixel each way: ≤1M samples for a 4096² preview
PERCENTILE_STEP = 4

MAX_8BIT = 255
MID_GRAY = 128
LOSSY_QUALITY = 85


class Encoding(Enum):
    LOSSLESS = "lossless"  # Screenshots: keeps text crisp
    LOSSY = "lossy"  # Photos and exports: much smaller


@dataclass(frozen=True)
class Renditions:
    preview: bytes
    thumb: bytes
    width: int  # Original size, as displayed after EXIF orientation
    height: int


def build(img: PILImage.Image, encoding: Encoding) -> Renditions:
    """Encode WebP preview and thumb copies of ``img``. Raises OSError/ValueError on undecodable pixels."""
    ImageOps.exif_transpose(img, in_place=True)
    width, height = img.size

    # Shrink before converting: keeps 16-bit math on the small image
    preview = _to_display(_shrink(img, PREVIEW_MAX_PX))
    thumb = _shrink(preview, THUMB_MAX_PX)

    return Renditions(
        preview=_encode(preview, encoding),
        thumb=_encode(thumb, encoding),
        width=width,
        height=height,
    )


def _shrink(img: PILImage.Image, max_px: int) -> PILImage.Image:
    """Fit within ``max_px`` square, keeping aspect and never upscaling, e.g. 8000×6000 → 4096×3072."""
    if img.mode in INDEXED_MODES:
        img = img.convert("RGBA" if img.has_transparency_data else "RGB")

    scale = max_px / max(img.size)
    if scale >= 1:
        return img

    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))

    # resize(), unlike thumbnail(), works on 16-bit modes
    return img.resize(size, LANCZOS)


def _to_display(img: PILImage.Image) -> PILImage.Image:
    """Convert to a mode browsers render: 8-bit gray or RGB(A)."""
    if img.mode in HIGH_DEPTH_MODES:
        return _stretch(img)

    if img.mode in WEB_MODES:
        return img

    # e.g. CMYK JPEG
    return img.convert("RGBA" if img.has_transparency_data else "RGB")


def _stretch(img: PILImage.Image) -> PILImage.Image:
    """Map the 0.5–99.5 percentile window onto 0–255. Flat images turn mid-gray; NaN/inf turn black."""
    pixels = np.array(img, dtype=np.float32)

    # Percentiles from a subsample: same window, a fraction of the sort cost
    sample = pixels[::PERCENTILE_STEP, ::PERCENTILE_STEP]
    finite = sample[np.isfinite(sample)]
    if finite.size == 0:
        return PILImage.new("L", img.size, MID_GRAY)

    lo, hi = np.percentile(finite, STRETCH_PERCENTILES)
    if hi <= lo:
        return PILImage.new("L", img.size, MID_GRAY)

    # In place: a 4096² preview is 64 MB per float copy
    np.subtract(pixels, lo, out=pixels)
    np.multiply(pixels, MAX_8BIT / (hi - lo), out=pixels)
    np.nan_to_num(pixels, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    np.clip(pixels, 0, MAX_8BIT, out=pixels)

    return PILImage.fromarray(pixels.astype(np.uint8))


def _encode(img: PILImage.Image, encoding: Encoding) -> bytes:
    buf = io.BytesIO()

    # No exif= argument, so metadata (camera, GPS) is dropped
    if encoding is Encoding.LOSSLESS:
        img.save(buf, "WEBP", lossless=True)
    else:
        img.save(buf, "WEBP", quality=LOSSY_QUALITY)

    return buf.getvalue()
