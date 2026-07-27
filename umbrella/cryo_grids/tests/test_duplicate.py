import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from cryo_grids.models import (
    CryoGrid,
    CryoGridBox,
    GridLabel,
    Label,
    PlungeFreezingDevice,
    PlungeFreezingSession,
    Puck,
    Site,
    Specimen,
)
from cryo_grids.services import DuplicateGridError, duplicate_grid, get_available_positions


@pytest.fixture
def user(db):
    return User.objects.create_user(username="duper", password="pw")


@pytest.fixture
def original_user(db):
    return User.objects.create_user(username="original", password="pw")


@pytest.fixture
def site(db):
    return Site.objects.create(name="site")


@pytest.fixture
def device(db, site):
    return PlungeFreezingDevice.objects.create(name="dev", site=site)


@pytest.fixture
def session(db, original_user, device):
    return PlungeFreezingSession.objects.create(user=original_user, device=device)


@pytest.fixture
def specimen(db):
    return Specimen.objects.create()


@pytest.fixture
def puck(db, original_user):
    return Puck.objects.create(name="1", user=original_user)


@pytest.fixture
def source_box(db, puck):
    return CryoGridBox.objects.create(name="src", puck=puck, position_in_puck=1, max_grids=4)


@pytest.fixture
def dest_box(db, puck):
    return CryoGridBox.objects.create(name="dst", puck=puck, position_in_puck=2, max_grids=4)


@pytest.fixture
def source_grid(db, original_user, session, specimen, source_box):
    return CryoGrid.objects.create(
        name="g",
        user=original_user,
        freezing_session=session,
        specimen=specimen,
        grid_box=source_box,
        position_in_box=1,
    )


@pytest.mark.django_db
class TestDuplicateGridService:
    def test_single_copy(self, source_grid, dest_box, user):
        [new_grid] = duplicate_grid(
            source_grid=source_grid, destination_box=dest_box, number_to_copy=1, request_user=user
        )
        assert new_grid.id != source_grid.id
        assert new_grid.grid_box == dest_box
        assert new_grid.position_in_box == 1
        assert new_grid.copy_number == 2  # source is copy 1
        assert new_grid.trashed is False
        assert new_grid.grid_cassette is None
        assert new_grid.slot_number_in_cassette is None

    def test_multi_copy_assigns_distinct_positions(self, source_grid, dest_box, user):
        copies = duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=3, request_user=user)
        assert sorted(c.position_in_box for c in copies) == [1, 2, 3]
        assert sorted(c.copy_number for c in copies) == [2, 3, 4]

    def test_copy_skips_occupied_positions(self, source_grid, dest_box, user, original_user, session, specimen):
        # Pre-occupy positions 1 and 3 in dest_box.
        CryoGrid.objects.create(
            name="other1",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=dest_box,
            position_in_box=1,
        )
        CryoGrid.objects.create(
            name="other2",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=dest_box,
            position_in_box=3,
        )
        copies = duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=2, request_user=user)
        assert sorted(c.position_in_box for c in copies) == [2, 4]

    def test_too_many_copies_raises(self, source_grid, dest_box, user):
        with pytest.raises(DuplicateGridError):
            duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=5, request_user=user)

    def test_partial_failure_rolls_back(self, source_grid, dest_box, user):
        """Fail mid-way: no copies should exist after the exception."""
        before = CryoGrid.objects.count()
        with pytest.raises(DuplicateGridError):
            duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=99, request_user=user)
        assert CryoGrid.objects.count() == before

    def test_trashed_source_rejected(self, source_grid, dest_box, user):
        source_grid.trashed = True
        source_grid.save()
        with pytest.raises(DuplicateGridError):
            duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=1, request_user=user)

    def test_labels_copied_with_duplicator_as_added_by(self, source_grid, dest_box, user, original_user):
        label = Label.objects.create(name="lbl", color="#fff")
        GridLabel.objects.create(grid=source_grid, label=label, added_by=original_user)

        [new_grid] = duplicate_grid(
            source_grid=source_grid, destination_box=dest_box, number_to_copy=1, request_user=user
        )
        new_labels = GridLabel.objects.filter(grid=new_grid)
        assert new_labels.count() == 1
        assert new_labels.first().added_by == user
        assert new_labels.first().label == label

    def test_trashed_grid_position_is_reused(self, source_grid, dest_box, user, original_user, session, specimen):
        CryoGrid.objects.create(
            name="ghost",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=dest_box,
            position_in_box=1,
            trashed=True,
        )
        [copy] = duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=1, request_user=user)
        assert copy.position_in_box == 1

    def test_zero_copies_rejected(self, source_grid, dest_box, user):
        with pytest.raises(DuplicateGridError):
            duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=0, request_user=user)

    def test_copy_number_follows_family_max(
        self, source_grid, dest_box, user, original_user, session, specimen, source_box
    ):
        """copy_number is (max existing copy_number in same (name, session, specimen) + 1)."""
        # Pre-create siblings at copy_number 2 and 3. They share name/session/specimen
        # with source_grid (which is copy 1) but live in the source box at positions 2 and 3.
        CryoGrid.objects.create(
            name=source_grid.name,
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=source_box,
            position_in_box=2,
            copy_number=2,
        )
        CryoGrid.objects.create(
            name=source_grid.name,
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=source_box,
            position_in_box=3,
            copy_number=3,
        )
        [new_grid] = duplicate_grid(
            source_grid=source_grid, destination_box=dest_box, number_to_copy=1, request_user=user
        )
        assert new_grid.copy_number == 4

    def test_copy_number_when_source_is_not_copy_one(
        self, dest_box, user, original_user, session, specimen, source_box
    ):
        """Duplicating a source that is itself a later copy still uses the family max, not source.copy_number."""
        # Family has copies 1, 2. Source is copy 2.
        CryoGrid.objects.create(
            name="family",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=source_box,
            position_in_box=1,
            copy_number=1,
        )
        source = CryoGrid.objects.create(
            name="family",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=source_box,
            position_in_box=2,
            copy_number=2,
        )
        [new_grid] = duplicate_grid(source_grid=source, destination_box=dest_box, number_to_copy=1, request_user=user)
        assert new_grid.copy_number == 3

    def test_consecutive_duplicates_keep_climbing(self, source_grid, dest_box, user):
        [first] = duplicate_grid(source_grid=source_grid, destination_box=dest_box, number_to_copy=1, request_user=user)
        [second] = duplicate_grid(
            source_grid=source_grid, destination_box=dest_box, number_to_copy=1, request_user=user
        )
        assert first.copy_number == 2
        assert second.copy_number == 3


@pytest.mark.django_db
class TestGetAvailablePositions:
    def test_empty_box(self, dest_box):
        assert get_available_positions(dest_box) == [1, 2, 3, 4]

    def test_with_used_and_trashed(self, dest_box, original_user, session, specimen):
        CryoGrid.objects.create(
            name="a",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=dest_box,
            position_in_box=2,
        )
        CryoGrid.objects.create(
            name="b",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=dest_box,
            position_in_box=3,
            trashed=True,
        )
        assert get_available_positions(dest_box) == [1, 3, 4]


@pytest.mark.django_db
class TestDuplicateEndpoint:
    def test_post_creates_copies(self, source_grid, dest_box, user):
        client = APIClient()
        client.force_login(user)
        url = f"/cryo_grids/v1/grids/{source_grid.id}/duplicate/"
        resp = client.post(
            url,
            {"destination_grid_box_id": dest_box.id, "number_to_copy": 2},
            format="json",
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["success"] is True
        assert len(body["new_grid_ids"]) == 2

    def test_post_missing_fields_returns_400(self, source_grid, user):
        client = APIClient()
        client.force_login(user)
        resp = client.post(f"/cryo_grids/v1/grids/{source_grid.id}/duplicate/", {}, format="json")
        assert resp.status_code == 400

    def test_post_unknown_grid_returns_404(self, user, dest_box):
        client = APIClient()
        client.force_login(user)
        resp = client.post(
            "/cryo_grids/v1/grids/9999999/duplicate/",
            {"destination_grid_box_id": dest_box.id, "number_to_copy": 1},
            format="json",
        )
        assert resp.status_code == 404

    def test_post_unknown_box_returns_404(self, source_grid, user):
        client = APIClient()
        client.force_login(user)
        resp = client.post(
            f"/cryo_grids/v1/grids/{source_grid.id}/duplicate/",
            {"destination_grid_box_id": 9999999, "number_to_copy": 1},
            format="json",
        )
        assert resp.status_code == 404

    def test_post_overflow_returns_400(self, source_grid, dest_box, user):
        client = APIClient()
        client.force_login(user)
        resp = client.post(
            f"/cryo_grids/v1/grids/{source_grid.id}/duplicate/",
            {"destination_grid_box_id": dest_box.id, "number_to_copy": 99},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAvailablePositionsEndpoint:
    def test_empty_box(self, dest_box, user):
        client = APIClient()
        client.force_login(user)
        resp = client.get(f"/cryo_grids/v1/grid-boxes/available_positions/?box_id={dest_box.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["available_count"] == 4
        assert body["available_positions"] == [1, 2, 3, 4]
        assert body["used_positions"] == []
        assert body["max_grids"] == 4

    def test_partial(self, dest_box, user, original_user, session, specimen):
        CryoGrid.objects.create(
            name="x",
            user=original_user,
            freezing_session=session,
            specimen=specimen,
            grid_box=dest_box,
            position_in_box=2,
        )
        client = APIClient()
        client.force_login(user)
        resp = client.get(f"/cryo_grids/v1/grid-boxes/available_positions/?box_id={dest_box.id}")
        body = resp.json()
        assert body["available_positions"] == [1, 3, 4]
        assert body["used_positions"] == [2]

    def test_unknown_box(self, user):
        client = APIClient()
        client.force_login(user)
        resp = client.get("/cryo_grids/v1/grid-boxes/available_positions/?box_id=9999999")
        assert resp.status_code == 404

    def test_missing_box_id(self, user):
        client = APIClient()
        client.force_login(user)
        resp = client.get("/cryo_grids/v1/grid-boxes/available_positions/")
        assert resp.status_code == 400
