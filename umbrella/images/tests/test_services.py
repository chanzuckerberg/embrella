import pytest
from django.core.files.storage import default_storage
from django.http import FileResponse
from PIL import Image as PILImage
from projects.models import Project

from images import services
from images.constants import Rendition
from images.models import Image
from images.services import InvalidImageError
from images.tests.uploads import encode, png_upload, tiff16_upload, upload

ACCEL_PREFIX = "/protected-media/"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_ACCEL_PREFIX = ""
    return tmp_path


def stored_names(image: Image) -> list[str]:
    return [image.original.name, image.preview.name, image.thumb.name]


@pytest.mark.django_db
class TestIngest:
    def test_png_is_stored_with_copies(self, test_user):
        image = services.ingest(png_upload(size=(64, 48)), test_user, notes="square B4 cracked")

        assert all(default_storage.exists(name) for name in stored_names(image))
        assert image.original.name.endswith(f"{image.id}.png")
        assert image.preview.name.endswith(f"{image.id}_preview.webp")
        assert (image.width, image.height) == (64, 48)
        assert image.content_type == "image/png"
        assert image.original_name == "shot.png"
        assert image.notes == "square B4 cracked"
        assert image.uploaded_by == test_user

    def test_16bit_tiff_is_accepted(self, test_user):
        image = services.ingest(tiff16_upload(), test_user)

        assert image.content_type == "image/tiff"
        assert image.original.name.endswith(".tif")

    def test_link_runs_with_the_row(self, test_user):
        linked = []

        image = services.ingest(png_upload(), test_user, link=linked.append)

        assert linked == [image]

    def test_failed_link_leaves_no_files_or_row(self, test_user, media_root):
        def broken_link(image):
            raise RuntimeError("link failed")

        with pytest.raises(RuntimeError):
            services.ingest(png_upload(), test_user, link=broken_link)

        assert not Image.objects.exists()
        assert not [path for path in media_root.rglob("*") if path.is_file()]

    @pytest.mark.parametrize(
        ("data", "name", "message"),
        [
            (b"not an image", "notes.txt", "Not a readable image"),
            (b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "x.svg", "Not a readable"),
            (encode(PILImage.new("RGB", (8, 8)), "GIF"), "anim.gif", "GIF isn't supported"),
            (encode(PILImage.new("RGB", (8, 8)), "BMP"), "x.bmp", "BMP isn't supported"),
        ],
    )
    def test_rejects_unsupported_files(self, test_user, data, name, message):
        with pytest.raises(InvalidImageError, match=message):
            services.ingest(upload(data, name), test_user)

        assert not Image.objects.exists()

    def test_rejects_multipage_tiff(self, test_user):
        pages = [PILImage.new("L", (8, 8)), PILImage.new("L", (8, 8))]
        data = encode(pages[0], "TIFF", save_all=True, append_images=pages[1:])

        with pytest.raises(InvalidImageError, match="single page"):
            services.ingest(upload(data, "stack.tif"), test_user)

    def test_rejects_oversized_file(self, test_user, monkeypatch):
        monkeypatch.setattr(services, "MAX_UPLOAD_BYTES", 10)

        with pytest.raises(InvalidImageError, match="max is"):
            services.ingest(png_upload(), test_user)

    def test_rejects_too_many_pixels(self, test_user, monkeypatch):
        monkeypatch.setattr(services, "MAX_IMAGE_PIXELS", 100)

        with pytest.raises(InvalidImageError, match="MP"):
            services.ingest(png_upload(size=(20, 20)), test_user)

    def test_rejects_truncated_file(self, test_user):
        data = encode(PILImage.new("RGB", (64, 64)), "PNG")

        with pytest.raises(InvalidImageError):
            services.ingest(upload(data[: len(data) // 2], "cut.png"), test_user)


@pytest.mark.django_db
class TestEdits:
    def test_set_project_moves_only_stale_rows(self, test_user):
        project = Project.objects.create(name="BD01")
        image = services.ingest(png_upload(), test_user)

        assert services.set_project([image.pk], project) == 1
        assert services.set_project([image.pk], project) == 0

        image.refresh_from_db()
        assert image.project == project

    def test_set_project_to_none(self, test_user):
        image = services.ingest(png_upload(), test_user, project=Project.objects.create(name="BD01"))

        services.set_project([image.pk], None)

        image.refresh_from_db()
        assert image.project is None

    def test_update_notes_skips_history(self, test_user):
        image = services.ingest(png_upload(), test_user)

        services.update_notes(image, "ice too thick")

        image.refresh_from_db()
        assert image.notes == "ice too thick"
        assert image.history.count() == 1

    def test_delete_removes_files_after_commit(self, test_user, django_capture_on_commit_callbacks):
        image = services.ingest(png_upload(), test_user)
        names = stored_names(image)

        with django_capture_on_commit_callbacks(execute=True):
            services.delete(image)

        assert not Image.objects.exists()
        assert not any(default_storage.exists(name) for name in names)


@pytest.mark.django_db
class TestServe:
    def test_preview_streams_inline_webp(self, test_user):
        image = services.ingest(png_upload(), test_user)

        response = services.serve(image, Rendition.PREVIEW)

        assert isinstance(response, FileResponse)
        assert response["Content-Type"] == "image/webp"
        assert response["Content-Disposition"].startswith("inline")
        assert response["X-Content-Type-Options"] == "nosniff"
        response.close()

    def test_original_downloads_under_uploaded_name(self, test_user):
        image = services.ingest(tiff16_upload(name="atlas B4.tif"), test_user)

        response = services.serve(image, Rendition.ORIGINAL)

        assert response["Content-Type"] == "image/tiff"
        assert response["Content-Disposition"] == 'attachment; filename="atlas B4.tif"'
        response.close()

    def test_accel_prefix_hands_off_to_nginx(self, test_user, settings):
        settings.MEDIA_ACCEL_PREFIX = ACCEL_PREFIX
        image = services.ingest(png_upload(), test_user)

        response = services.serve(image, Rendition.THUMB)

        assert response["X-Accel-Redirect"] == f"{ACCEL_PREFIX}{image.thumb.name}"
        assert response.content == b""
