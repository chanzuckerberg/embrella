"""Image storage and serving. The only API other apps call.

    upload ──► ingest(): validate ─► renditions.build() ─► write files ─► Image row (+ owner link)
    request ─► serve():  X-Accel-Redirect (prod nginx) | FileResponse (dev runserver)

Owners (e.g. cryo_grids.GridImage) link to an Image; this app never imports them.
"""

import os
from collections.abc import Callable, Iterable
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.utils.http import content_disposition_header
from PIL import Image as PILImage
from projects.models import Project

from images import renditions
from images.constants import CACHE_MAX_AGE_S, MAX_IMAGE_PIXELS, MAX_UPLOAD_BYTES, Rendition
from images.models import Image
from images.renditions import Encoding

# Pillow format → (stored extension, display-copy encoding). Anything else is rejected.
FORMATS = {
    "PNG": ("png", Encoding.LOSSLESS),
    "JPEG": ("jpg", Encoding.LOSSY),
    "WEBP": ("webp", Encoding.LOSSY),
    "TIFF": ("tif", Encoding.LOSSY),
}

RENDITION_CONTENT_TYPE = "image/webp"
BYTES_PER_MB = 1024 * 1024
PIXELS_PER_MP = 1_000_000

# Errors Pillow raises for files it can't parse
UNREADABLE_ERRORS = (PILImage.UnidentifiedImageError, OSError, SyntaxError, ValueError)


class InvalidImageError(Exception):
    """Upload rejected. The message is safe to show users."""


def ingest(
    upload,
    user,
    *,
    project: Project | None = None,
    notes: str = "",
    link: Callable[[Image], object] | None = None,
) -> Image:
    """Validate ``upload``, store it with display copies and create the row.

    ``link`` runs in the same transaction, e.g. to create the owner's link row.
    On any failure the files already written are deleted, then the error is raised.
    """
    if upload.size > MAX_UPLOAD_BYTES:
        raise InvalidImageError(
            f"File is {upload.size / BYTES_PER_MB:.0f} MB; max is {MAX_UPLOAD_BYTES // BYTES_PER_MB} MB."
        )

    img = _open(upload)
    extension, encoding = FORMATS[img.format]
    content_type = PILImage.MIME[img.format]
    try:
        copies = renditions.build(img, encoding)
    except (OSError, ValueError) as exc:
        raise InvalidImageError(
            "Couldn't decode this image; the file may be truncated or use unsupported compression."
        ) from exc

    # Free decoded pixels before writing. Not close(): Pillow would close the upload too.
    del img

    image = Image(
        project=project,
        original_name=os.path.basename(upload.name)[: Image._meta.get_field("original_name").max_length],
        content_type=content_type,
        size_bytes=upload.size,
        width=copies.width,
        height=copies.height,
        notes=notes,
        uploaded_by=user,
    )

    # Files first, so a row never points at a missing file
    written = []
    try:
        upload.seek(0)
        _write(image.original, f"{image.id}.{extension}", upload, written)
        _write(image.preview, f"{image.id}_preview.webp", ContentFile(copies.preview), written)
        _write(image.thumb, f"{image.id}_thumb.webp", ContentFile(copies.thumb), written)

        with transaction.atomic():
            image.save()
            if link:
                link(image)
    except Exception:
        _delete_files(written)
        raise

    return image


def set_project(image_ids: Iterable, project: Project | None) -> int:
    """Point images at ``project``, e.g. after their grid moved. Skips rows already correct."""
    images = Image.objects.filter(pk__in=image_ids)
    stale = images.filter(project__isnull=False) if project is None else images.exclude(project=project)

    return stale.update(project=project)


def update_notes(image: Image, notes: str) -> None:
    image.notes = notes

    # Notes aren't tracked, so a history row would be empty
    image.save_without_historical_record(update_fields=["notes"])


def delete(image: Image) -> None:
    """Delete the row now and its files after commit, so a rolled-back delete keeps them."""
    names = [file.name for file in (image.original, image.preview, image.thumb) if file]
    image.delete()

    transaction.on_commit(lambda: _delete_files(names))


def serve(image: Image, rendition: Rendition) -> HttpResponse:
    """Response for one of ``image``'s files. Originals download under their uploaded name."""
    file = getattr(image, rendition.value)
    is_original = rendition is Rendition.ORIGINAL
    content_type = image.content_type if is_original else RENDITION_CONTENT_TYPE

    # nginx streams the file; Django only checked the request
    if settings.MEDIA_ACCEL_PREFIX:
        response = HttpResponse(content_type=content_type)
        response["X-Accel-Redirect"] = f"{settings.MEDIA_ACCEL_PREFIX.rstrip('/')}/{quote(file.name)}"
    else:
        response = FileResponse(file.open("rb"), content_type=content_type)

    filename = image.original_name if is_original else os.path.basename(file.name)
    response["Content-Disposition"] = content_disposition_header(is_original, filename)

    # Trust our content type; a file disguised as an image can't run as HTML
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = f"private, max-age={CACHE_MAX_AGE_S}"

    return response


def _open(upload) -> PILImage.Image:
    """Open ``upload`` lazily (header only) and reject anything we don't accept."""
    try:
        # verify() checks integrity but leaves the image unusable, so reopen after
        with PILImage.open(upload) as probe:
            probe.verify()
        upload.seek(0)
        img = PILImage.open(upload)
    except PILImage.DecompressionBombError as exc:
        raise InvalidImageError(f"Image is too large; max is {MAX_IMAGE_PIXELS // PIXELS_PER_MP} MP.") from exc
    except UNREADABLE_ERRORS as exc:
        raise InvalidImageError("Not a readable image. Upload PNG, JPEG, WebP or TIFF.") from exc

    error = _rejection(img)
    if error:
        img.close()
        raise InvalidImageError(error)

    return img


def _rejection(img: PILImage.Image) -> str:
    """Why ``img`` is refused, or "" if accepted."""
    if img.format not in FORMATS:
        return f"{img.format} isn't supported. Upload PNG, JPEG, WebP or TIFF."

    if getattr(img, "n_frames", 1) > 1:
        return "Multi-page or animated images aren't supported. Save a single page."

    pixels = img.width * img.height
    if pixels > MAX_IMAGE_PIXELS:
        return f"Image is {pixels / PIXELS_PER_MP:.0f} MP; max is {MAX_IMAGE_PIXELS // PIXELS_PER_MP} MP."

    return ""


def _write(field, name: str, content, written: list[str]) -> None:
    field.save(name, content, save=False)
    written.append(field.name)


def _delete_files(names: list[str]) -> None:
    for name in names:
        default_storage.delete(name)
