import pytest
from accounts.models import SystemFeatureFlag
from django.core.files.storage import default_storage
from images.constants import IMAGES_FLAG
from images.models import Image
from images.tests.uploads import png_upload, tiff16_upload, upload
from projects.models import Project

from cryo_grids import services
from cryo_grids.history import ChangeReason
from cryo_grids.models import CryoGrid, GridImage

MISSING_IMAGE_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_ACCEL_PREFIX = ""
    return tmp_path


@pytest.fixture
def images_on(db):
    # Seeded off by accounts migration 0008
    flag, _ = SystemFeatureFlag.objects.update_or_create(name=IMAGES_FLAG, defaults={"enabled": True})
    return flag


@pytest.fixture
def project(db):
    return Project.objects.create(name="BD01")


def images_url(grid) -> str:
    return f"/cryo_grids/v1/grids/{grid.id}/images/"


def post_image(client, grid, file, notes=""):
    return client.post(images_url(grid), {"file": file, "notes": notes})


def stored_files(image: Image) -> list[str]:
    return [image.original.name, image.preview.name, image.thumb.name]


@pytest.mark.django_db
class TestGridImagesApi:
    def test_upload_needs_the_flag(self, logged_in_client, test_grid):
        response = post_image(logged_in_client, test_grid, png_upload())

        assert response.status_code == 403
        assert not Image.objects.exists()

    def test_upload_and_list(self, logged_in_client, test_grid, images_on):
        first = post_image(logged_in_client, test_grid, png_upload(name="a.png"), notes="atlas")
        second = post_image(logged_in_client, test_grid, tiff16_upload(name="b.tif"))

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["notes"] == "atlas"
        assert set(first.json()["urls"]) == {"thumb", "preview", "original"}

        listed = logged_in_client.get(images_url(test_grid)).json()
        assert [image["original_name"] for image in listed] == ["a.png", "b.tif"]

    def test_invalid_upload_returns_message(self, logged_in_client, test_grid, images_on):
        response = post_image(logged_in_client, test_grid, upload(b"nope", "x.txt"))

        assert response.status_code == 400
        assert "Not a readable image" in response.json()["detail"]

    def test_trashed_grid_keeps_images(self, logged_in_client, test_grid, images_on):
        post_image(logged_in_client, test_grid, png_upload())
        test_grid.trashed = True
        test_grid.save()

        assert len(logged_in_client.get(images_url(test_grid)).json()) == 1

    def test_delete(self, logged_in_client, test_grid, images_on, django_capture_on_commit_callbacks):
        image_id = post_image(logged_in_client, test_grid, png_upload()).json()["id"]
        files = stored_files(Image.objects.get(pk=image_id))

        with django_capture_on_commit_callbacks(execute=True):
            response = logged_in_client.delete(f"{images_url(test_grid)}{image_id}/")

        assert response.status_code == 204
        assert not GridImage.objects.exists()
        assert not any(default_storage.exists(name) for name in files)

    def test_delete_from_another_grid_is_404(self, logged_in_client, test_grid, images_on):
        image_id = post_image(logged_in_client, test_grid, png_upload()).json()["id"]
        other = CryoGrid.objects.create(name="other", freezing_session=test_grid.freezing_session)

        response = logged_in_client.delete(f"{images_url(other)}{image_id}/")

        assert response.status_code == 404
        assert Image.objects.filter(pk=image_id).exists()

    def test_delete_unknown_image_is_404(self, logged_in_client, test_grid, images_on):
        response = logged_in_client.delete(f"{images_url(test_grid)}{MISSING_IMAGE_ID}/")

        assert response.status_code == 404

    def test_file_and_notes(self, logged_in_client, test_grid, images_on):
        image = post_image(logged_in_client, test_grid, png_upload()).json()

        file_response = logged_in_client.get(image["urls"]["thumb"])
        assert file_response.status_code == 200
        assert file_response["Content-Type"] == "image/webp"

        patched = logged_in_client.patch(
            f"/images/v1/images/{image['id']}/",
            {"notes": "cracked"},
            content_type="application/json",
        )
        assert patched.status_code == 200
        assert patched.json()["notes"] == "cracked"

    def test_bad_rendition_is_400(self, logged_in_client, test_grid, images_on):
        image = post_image(logged_in_client, test_grid, png_upload()).json()

        response = logged_in_client.get(f"/images/v1/images/{image['id']}/file/?r=huge")

        assert response.status_code == 400

    def test_anonymous_gets_no_file(self, client, logged_in_client, test_grid, images_on):
        image = post_image(logged_in_client, test_grid, png_upload()).json()
        logged_in_client.logout()

        assert client.get(image["urls"]["preview"]).status_code != 200


@pytest.mark.django_db
class TestProjectSync:
    def test_upload_takes_grid_project(self, test_user, test_grid, project):
        test_grid.intended_project = project
        test_grid.save()

        image = services.add_grid_image(test_grid, png_upload(), test_user)

        assert image.project == project

    def test_grid_save_moves_images(self, test_user, test_grid, project):
        image = services.add_grid_image(test_grid, png_upload(), test_user)

        test_grid.intended_project = project
        test_grid.save()

        image.refresh_from_db()
        assert image.project == project

    def test_bulk_update_moves_images(self, test_user, test_grid, project):
        image = services.add_grid_image(test_grid, png_upload(), test_user)

        services.update_grids([test_grid], reason=ChangeReason.EDITED, intended_project=project)

        image.refresh_from_db()
        assert image.project == project

    def test_project_delete_clears_link(self, test_user, test_grid, project):
        test_grid.intended_project = project
        test_grid.save()
        image = services.add_grid_image(test_grid, png_upload(), test_user)

        project.delete()

        image.refresh_from_db()
        assert image.project is None


@pytest.mark.django_db
class TestGridDelete:
    def test_hard_delete_removes_images(self, test_user, test_grid, django_capture_on_commit_callbacks):
        image = services.add_grid_image(test_grid, png_upload(), test_user)
        files = stored_files(image)

        with django_capture_on_commit_callbacks(execute=True):
            test_grid.delete()

        assert not Image.objects.exists()
        assert not any(default_storage.exists(name) for name in files)

    def test_duplicate_does_not_copy_images(self, test_user, test_grid, test_box_b):
        services.add_grid_image(test_grid, png_upload(), test_user)

        [copy] = services.duplicate_grid(
            source_grid=test_grid,
            destination_box=test_box_b,
            number_to_copy=1,
            request_user=test_user,
        )

        assert not GridImage.objects.filter(grid=copy).exists()
