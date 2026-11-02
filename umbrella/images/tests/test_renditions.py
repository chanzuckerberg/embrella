import io

import numpy as np
import pytest
from PIL import Image as PILImage

from images import renditions
from images.constants import PREVIEW_MAX_PX, THUMB_MAX_PX
from images.renditions import MID_GRAY, Encoding
from images.tests.uploads import encode, gradient_16bit

EXIF_ORIENTATION_TAG = 0x0112
ROTATED_90 = 6


def decode(data: bytes) -> PILImage.Image:
    img = PILImage.open(io.BytesIO(data))
    img.load()
    return img


class TestSizes:
    def test_small_image_keeps_its_size(self):
        copies = renditions.build(PILImage.new("RGB", (1920, 1080)), Encoding.LOSSLESS)

        assert decode(copies.preview).size == (1920, 1080)
        assert decode(copies.thumb).size == (THUMB_MAX_PX, 144)
        assert (copies.width, copies.height) == (1920, 1080)

    def test_large_image_fits_preview(self):
        copies = renditions.build(PILImage.new("L", (PREVIEW_MAX_PX * 2, 100)), Encoding.LOSSY)

        assert decode(copies.preview).size == (PREVIEW_MAX_PX, 50)
        assert (copies.width, copies.height) == (PREVIEW_MAX_PX * 2, 100)

    def test_tiny_image_is_never_upscaled(self):
        copies = renditions.build(PILImage.new("RGB", (20, 10)), Encoding.LOSSLESS)

        assert decode(copies.preview).size == (20, 10)
        assert decode(copies.thumb).size == (20, 10)

    def test_exif_orientation_is_applied(self):
        exif = PILImage.Exif()
        exif[EXIF_ORIENTATION_TAG] = ROTATED_90
        img = PILImage.open(io.BytesIO(encode(PILImage.new("RGB", (40, 20)), "JPEG", exif=exif)))

        copies = renditions.build(img, Encoding.LOSSY)

        assert decode(copies.preview).size == (20, 40)
        assert (copies.width, copies.height) == (20, 40)


class TestPixels:
    def test_16bit_is_stretched_to_full_range(self):
        copies = renditions.build(gradient_16bit(), Encoding.LOSSLESS)

        pixels = np.asarray(decode(copies.preview).convert("L"))
        assert pixels.min() == 0
        assert pixels.max() == 255

    @pytest.mark.parametrize("value", [3000, np.nan])
    def test_flat_or_empty_float_turns_mid_gray(self, value):
        img = PILImage.fromarray(np.full((10, 10), value, dtype=np.float32))

        copies = renditions.build(img, Encoding.LOSSLESS)

        assert set(np.unique(np.asarray(decode(copies.preview).convert("L")))) == {MID_GRAY}

    def test_nan_pixels_turn_black(self):
        pixels = np.tile(np.linspace(0, 1, 50, dtype=np.float32), (10, 1))
        pixels[0, 0] = np.nan

        copies = renditions.build(PILImage.fromarray(pixels), Encoding.LOSSLESS)

        assert np.asarray(decode(copies.preview).convert("L"))[0, 0] == 0

    def test_8bit_is_not_stretched(self):
        img = PILImage.new("L", (10, 10), 100)

        copies = renditions.build(img, Encoding.LOSSLESS)

        assert set(np.unique(np.asarray(decode(copies.preview).convert("L")))) == {100}

    @pytest.mark.parametrize("mode", ["CMYK", "P", "1", "LA", "RGBA"])
    def test_any_mode_encodes_as_webp(self, mode):
        copies = renditions.build(PILImage.new(mode, (30, 20)), Encoding.LOSSY)

        assert decode(copies.preview).format == "WEBP"
        assert decode(copies.thumb).format == "WEBP"

    def test_metadata_is_dropped(self):
        exif = PILImage.Exif()
        exif[0x010F] = "SecretCamera"  # Make
        img = PILImage.open(io.BytesIO(encode(PILImage.new("RGB", (30, 20)), "JPEG", exif=exif)))

        copies = renditions.build(img, Encoding.LOSSY)

        assert not decode(copies.preview).getexif()
