"""GET /timeline/v1/grids/<id>/ — grid, label, container, MSI session and proc run entries."""

from datetime import timedelta

import pytest
from cryo_grids.history import ChangeReason
from cryo_grids.models import (
    Cane,
    CryoGrid,
    CryoGridBox,
    Dewar,
    GridLabel,
    Label,
    PlungeFreezingDevice,
    PlungeFreezingSession,
    Puck,
    Site,
)
from django.contrib.auth.models import User
from django.utils import timezone
from processes.models import ProcRun

from timeline.types import EntryKind, Subject


@pytest.fixture
def user(db):
    return User.objects.create_user(username="historian", password="testpass")


@pytest.fixture
def site(db):
    return Site.objects.create(name="SiteA")


@pytest.fixture
def puck(db, site):
    dewar = Dewar.objects.create(name="DewarA", site=site)
    cane = Cane.objects.create(name="CaneA", dewar=dewar, position_in_dewar=1)
    return Puck.objects.create(name="PuckA", cane=cane, position_in_cane=1)


@pytest.fixture
def box_a(db, puck):
    return CryoGridBox.objects.create(name="BoxA", puck=puck, position_in_puck=1)


@pytest.fixture
def box_b(db, puck):
    return CryoGridBox.objects.create(name="BoxB", puck=puck, position_in_puck=2)


@pytest.fixture
def grid(db, user, site, box_a):
    device = PlungeFreezingDevice.objects.create(name="Device", site=site)
    session = PlungeFreezingSession.objects.create(user=user, device=device)
    return CryoGrid.objects.create(name="grid1", user=user, freezing_session=session, grid_box=box_a, position_in_box=1)


@pytest.fixture
def client_in(client, user):
    client.force_login(user)
    return client


def timeline(client, grid_id):
    response = client.get(f"/timeline/v1/grids/{grid_id}/")
    assert response.status_code == 200
    return response.json()


def kinds(entries):
    return [e["kind"] for e in entries]


def moved_via(entries, via):
    return [e for e in entries if e["kind"] == EntryKind.MOVED and e["detail"].get("via") == via]


@pytest.mark.django_db
class TestEndpoint:
    def test_unknown_grid_404(self, client_in):
        assert client_in.get("/timeline/v1/grids/999999/").status_code == 404

    def test_requires_login(self, client, grid):
        assert client.get(f"/timeline/v1/grids/{grid.id}/").status_code in (401, 403)

    def test_created(self, client_in, grid):
        (entry,) = timeline(client_in, grid.id)

        assert entry["kind"] == EntryKind.CREATED
        assert entry["subject"] == Subject.GRID
        assert entry["subject_id"] == grid.id


@pytest.mark.django_db
class TestGridEntries:
    def test_move(self, client_in, user, grid, box_b):
        client_in.patch(
            f"/cryo_grids/v1/grids/{grid.id}/move/",
            data={"destination_grid_box_id": box_b.id, "destination_position": 2},
            content_type="application/json",
        )

        entry = timeline(client_in, grid.id)[0]
        assert entry["kind"] == EntryKind.MOVED
        assert entry["summary"] == "Grid moved: BoxA position 1 to BoxB position 2"
        assert entry["user"] == user.username

    def test_move_within_box(self, client_in, grid, box_a):
        client_in.patch(
            f"/cryo_grids/v1/grids/{grid.id}/move/",
            data={"destination_grid_box_id": box_a.id, "destination_position": 4},
            content_type="application/json",
        )

        assert timeline(client_in, grid.id)[0]["summary"] == "Grid moved: same box, position 1 to 4"

    def test_trashed_grid_still_served(self, client_in, grid):
        client_in.post(
            f"/cryo_grids/update-grid-trashed/{grid.id}/",
            data={"trashed": True},
            content_type="application/json",
        )

        assert kinds(timeline(client_in, grid.id)) == [EntryKind.TRASHED, EntryKind.CREATED]

    def test_trash_cause(self, client_in, grid, box_a):
        client_in.delete(f"/api/list/pucks/grid-box/{box_a.id}/")

        assert timeline(client_in, grid.id)[0]["summary"] == "Trashed (box deleted)"

    def test_edit_names_fields(self, client_in, grid):
        client_in.patch(
            f"/cryo_grids/v1/grids/{grid.id}/update/",
            data={"blot_time": 4.5},
            content_type="application/json",
        )

        assert timeline(client_in, grid.id)[0]["summary"] == "Edited blot time"

    def test_no_reason_classified_from_diff(self, client_in, grid):
        grid.clipped = True
        grid.save()  # e.g. admin edit: no reason

        assert timeline(client_in, grid.id)[0]["kind"] == EntryKind.CLIPPED

    def test_noop_save_skipped(self, client_in, grid):
        grid.save()

        assert kinds(timeline(client_in, grid.id)) == [EntryKind.CREATED]

    def test_newest_first(self, client_in, grid, box_b):
        grid.clipped = True
        grid.save()
        grid.grid_box = box_b
        grid.save()

        assert kinds(timeline(client_in, grid.id)) == [EntryKind.MOVED, EntryKind.CLIPPED, EntryKind.CREATED]


@pytest.mark.django_db
class TestLabels:
    def test_added_and_removed(self, client_in, user, grid):
        label = Label.objects.create(name="timeline-test", color="#43a047")
        # Labels < 1 min old are auto-deleted once unused (typo cleanup); age it to keep its name
        Label.objects.filter(id=label.id).update(created_at=timezone.now() - timedelta(hours=1))
        url = f"/cryo_grids/v1/grids/{grid.id}/update-labels/"
        client_in.patch(url, data={"label_ids": [label.id]}, content_type="application/json")
        client_in.patch(url, data={"label_ids": []}, content_type="application/json")

        removed, added = timeline(client_in, grid.id)[:2]
        assert (added["kind"], removed["kind"]) == (EntryKind.LABEL_ADDED, EntryKind.LABEL_REMOVED)
        assert added["summary"] == "Label timeline-test added"
        assert added["user"] == user.username


@pytest.mark.django_db
class TestBaseline:
    """Pre-install objects get a ``baseline`` snapshot (migration 0039)."""

    def test_grid_created_at_create_on_by_owner(self, client_in, user, grid):
        grid.history.all().delete()
        CryoGrid.history.bulk_history_create([grid], default_change_reason=ChangeReason.BASELINE)

        (entry,) = timeline(client_in, grid.id)
        assert entry["kind"] == EntryKind.CREATED
        assert entry["at"].startswith(grid.create_on.isoformat())
        assert entry["user"] == user.username

    def test_label_added_at_added_at(self, client_in, user, grid):
        label = Label.objects.create(name="old-label")
        link = GridLabel.objects.create(grid=grid, label=label, added_by=user)
        GridLabel.history.all().delete()
        GridLabel.history.bulk_history_create([link], default_change_reason=ChangeReason.BASELINE)

        entry = next(e for e in timeline(client_in, grid.id) if e["kind"] == EntryKind.LABEL_ADDED)
        assert entry["user"] == user.username


@pytest.mark.django_db
class TestContainerMoves:
    def test_box_move_while_inside(self, client_in, user, grid, box_a, puck):
        other = Puck.objects.create(name="PuckB", cane=puck.cane, position_in_cane=2)
        client_in.patch(
            f"/api/list/pucks/grid-box/{box_a.id}/move/",
            data={"puck_id": other.id, "position_in_puck": 3},
            content_type="application/json",
        )

        (entry,) = moved_via(timeline(client_in, grid.id), "box")
        assert entry["summary"] == "Box moved: PuckA slot 1 to PuckB slot 3"
        assert entry["user"] == user.username

    def test_box_move_after_grid_left(self, client_in, grid, box_a, box_b, puck):
        grid.grid_box = box_b
        grid.save()
        box_a.position_in_puck = 5
        box_a.save()

        assert moved_via(timeline(client_in, grid.id), "box") == []

    def test_puck_move(self, client_in, grid, puck):
        client_in.patch(f"/api/list/pucks/{puck.id}/", data={"position_in_cane": 4}, content_type="application/json")

        (entry,) = moved_via(timeline(client_in, grid.id), "puck")
        assert entry["summary"] == "Puck moved: same cane, position 1 to 4"

    def test_puck_move_after_grid_left(self, client_in, grid, puck, box_b):
        other_puck = Puck.objects.create(name="PuckB", cane=puck.cane, position_in_cane=2)
        box_b.puck = other_puck
        box_b.save()
        grid.grid_box = box_b
        grid.save()

        puck.position_in_cane = 6
        puck.save()

        assert moved_via(timeline(client_in, grid.id), "puck") == []

    def test_cane_move(self, client_in, grid, puck):
        cane = puck.cane
        cane.position_in_dewar = 3
        cane.save()

        (entry,) = moved_via(timeline(client_in, grid.id), "cane")
        assert entry["summary"] == "Cane moved: same dewar, slot 1 to 3"

    def test_dewar_move(self, client_in, grid, puck):
        dewar = puck.cane.dewar
        dewar.site = Site.objects.create(name="SiteB")
        dewar.save()

        (entry,) = moved_via(timeline(client_in, grid.id), "dewar")
        assert entry["summary"] == "Dewar moved: SiteA to SiteB"


@pytest.mark.django_db
class TestMsiSessionsAndProcRuns:
    def test_included(self, client_in, grid, test_msi_session, test_proc_plan):
        test_msi_session.grid = grid
        test_msi_session.save()
        run = ProcRun.objects.create(name="run001", proc_plan=test_proc_plan, msi_session=test_msi_session)

        entries = timeline(client_in, grid.id)
        subjects = {(e["subject"], e["subject_id"]) for e in entries}

        assert (Subject.MSI_SESSION, test_msi_session.id) in subjects
        assert (Subject.PROC_RUN, run.id) in subjects
