"""Limits and names shared by the images app."""

from enum import StrEnum

# SystemFeatureFlag gating image uploads and edits
IMAGES_FLAG = "images"

# Matches nginx `client_max_body_size 100M`
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

# Processing memory grows with pixels; at 100 MP, peak ≈ 400 MB (16-bit gray) to 600 MB (RGB)
MAX_IMAGE_PIXELS = 100_000_000

# Longest side of each display copy; smaller images keep their size
PREVIEW_MAX_PX = 4096
THUMB_MAX_PX = 256

# Query parameter picking the file to serve, e.g. ?r=thumb
RENDITION_PARAM = "r"

# Browser cache lifetime for served files; files never change after upload
CACHE_MAX_AGE_S = 24 * 60 * 60


class Rendition(StrEnum):
    THUMB = "thumb"
    PREVIEW = "preview"
    ORIGINAL = "original"
