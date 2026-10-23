"""Build in-memory uploads for image tests, e.g. png_upload(size=(64, 48))."""

import io

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage

# 16-bit test signal: values in a narrow band, like a detector export
SIGNAL_LO = 1200
SIGNAL_HI = 4800


def encode(img: PILImage.Image, fmt: str, **save_kwargs) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, **save_kwargs)
    return buf.getvalue()


def upload(data: bytes, name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, data)


def png_upload(size=(64, 48), mode="RGB", name="shot.png") -> SimpleUploadedFile:
    return upload(encode(PILImage.new(mode, size, "red" if mode == "RGB" else 0), "PNG"), name)


def gradient_16bit(size=(80, 60)) -> PILImage.Image:
    """Horizontal ramp from SIGNAL_LO to SIGNAL_HI, as a 16-bit grayscale image."""
    width, height = size
    row = np.linspace(SIGNAL_LO, SIGNAL_HI, width, dtype=np.uint16)
    return PILImage.fromarray(np.tile(row, (height, 1)))


def tiff16_upload(size=(80, 60), name="export.tif") -> SimpleUploadedFile:
    return upload(encode(gradient_16bit(size), "TIFF"), name)
