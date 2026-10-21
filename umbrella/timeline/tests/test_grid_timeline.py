"""GET /timeline/v1/grids/<id>/ — grid, label, container, MSI session and proc run entries."""

from datetime import timedelta

import pytest
from cryo_grids.history import ChangeReason
from cryo_grids.models import (
    CryoGrid,
    GridLabel,
    Label,
    Puck,
    Site,
)
from django.utils import timezone
from processes.models import ProcRun

from timeline.types import EntryKind, Subject


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
    def test_unknown_grid_404(self, logged_in_client):
        assert logged_in_client.get("/timeline/v1/grids/999999/").status_code == 404

    def test_requires_login(self, client, test_grid):
        assert client.get(f"/timeline/v1/grids/{test_grid.id}/").status_code in (401, 403)

    def test_created(self, logged_in_client, test_grid):
        (entry,) = timeline(logged_in_client, test_grid.id)

        assert entry["kind"] == EntryKind.CREATED
        assert entry["subject"] == Subject.GRID
        assert entry["subject_id"] == test_grid.id


@pytest.mark.django_db
class TestGridEntries:
    def test_move(self, logged_in_client, test_user, test_grid, test_box_b):
        logged_in_client.patch(
            f"/cryo_grids/v1/grids/{test_grid.id}/move/",
            data={"destination_grid_box_id": test_box_b.id, "destination_position": 2},
            content_type="application/json",
        )

        entry = timeline(logged_in_client, test_grid.id)[0]
        assert entry["kind"] == EntryKind.MOVED
        assert entry["summary"] == "Grid moved: BoxA position 1 to BoxB position 2"
        assert entry["user"] == test_user.username

    def test_move_within_box(self, logged_in_client, test_grid, test_box_a):
        logged_in_client.patch(
            f"/cryo_grids/v1/grids/{test_grid.id}/move/",
            data={"destination_grid_box_id": test_box_a.id, "destination_position": 4},
            content_type="application/json",
        )

        assert timeline(logged_in_client, test_grid.id)[0]["summary"] == "Grid moved: same box, position 1 to 4"

    def test_trashed_grid_still_served(self, logged_in_client, test_grid):
        logged_in_client.post(
            f"/cryo_grids/update-grid-trashed/{test_grid.id}/",
            data={"trashed": True},
            content_type="application/json",
        )

        assert kinds(timeline(logged_in_client, test_grid.id)) == [EntryKind.TRASHED, EntryKind.CREATED]

    def test_trash_cause(self, logged_in_client, test_grid, test_box_a):
        logged_in_client.delete(f"/api/list/pucks/grid-box/{test_box_a.id}/")

        assert timeline(logged_in_client, test_grid.id)[0]["summary"] == "Trashed (box deleted)"

    def test_edit_names_fields(self, logged_in_client, test_grid):
        logged_in_client.patch(
            f"/cryo_grids/v1/grids/{test_grid.id}/update/",
            data={"blot_time": 4.5},
            content_type="application/json",
        )

        assert timeline(logged_in_client, test_grid.id)[0]["summary"] == "Edited blot time"

    def test_unchanged_edit_skipped(self, logged_in_client, test_grid):
        logged_in_client.patch(
            f"/cryo_grids/v1/grids/{test_grid.id}/update/",
            data={"name": test_grid.name, "blot_time": test_grid.blot_time},
            content_type="application/json",
        )

        assert kinds(timeline(logged_in_client, test_grid.id)) == [EntryKind.CREATED]

    def test_no_reason_classified_from_diff(self, logged_in_client, test_grid):
        test_grid.clipped = True
        test_grid.save()  # e.g. admin edit: no reason

        assert timeline(logged_in_client, test_grid.id)[0]["kind"] == EntryKind.CLIPPED

    def test_noop_save_skipped(self, logged_in_client, test_grid):
        test_grid.save()

        assert kinds(timeline(logged_in_client, test_grid.id)) == [EntryKind.CREATED]

    def test_newest_first(self, logged_in_client, test_grid, test_box_b):
        test_grid.clipped = True
        test_grid.save()
        test_grid.grid_box = test_box_b
        test_grid.save()

        assert kinds(timeline(logged_in_client, test_grid.id)) == [
            EntryKind.MOVED,
            EntryKind.CLIPPED,
            EntryKind.CREATED,
        ]


@pytest.mark.django_db
class TestLabels:
    def test_added_and_removed(self, logged_in_client, test_user, test_grid):
        label = Label.objects.create(name="timeline-test", color="#43a047")
        # Labels < 1 min old are auto-deleted once unused (typo cleanup); age it to keep its name
        Label.objects.filter(id=label.id).update(created_at=timezone.now() - timedelta(hours=1))
        url = f"/cryo_grids/v1/grids/{test_grid.id}/update-labels/"
        logged_in_client.patch(url, data={"label_ids": [label.id]}, content_type="application/json")
        logged_in_client.patch(url, data={"label_ids": []}, content_type="application/json")

        removed, added = timeline(logged_in_client, test_grid.id)[:2]
        assert (added["kind"], removed["kind"]) == (EntryKind.LABEL_ADDED, EntryKind.LABEL_REMOVED)
        assert added["summary"] == "Label timeline-test added"
        assert added["user"] == test_user.username


@pytest.mark.django_db
class TestBaseline:
    """Pre-install objects get a ``baseline`` snapshot (migration 0039)."""

    def test_grid_created_at_create_on_by_owner(self, logged_in_client, test_user, test_grid):
        test_grid.history.all().delete()
        CryoGrid.history.bulk_history_create([test_grid], default_change_reason=ChangeReason.BASELINE)

        (entry,) = timeline(logged_in_client, test_grid.id)
        assert entry["kind"] == EntryKind.CREATED
        assert entry["at"].startswith(test_grid.create_on.isoformat())
        assert entry["user"] == test_user.username

    def test_label_added_at_added_at(self, logged_in_client, test_user, test_grid):
        label = Label.objects.create(name="old-label")
        link = GridLabel.objects.create(grid=test_grid, label=label, added_by=test_user)
        GridLabel.history.all().delete()
        GridLabel.history.bulk_history_create([link], default_change_reason=ChangeReason.BASELINE)

        entry = next(e for e in timeline(logged_in_client, test_grid.id) if e["kind"] == EntryKind.LABEL_ADDED)
        assert entry["user"] == test_user.username


@pytest.mark.django_db
class TestContainerMoves:
    def test_box_move_while_inside(self, logged_in_client, test_user, test_grid, test_box_a, test_puck):
        other = Puck.objects.create(name="PuckB", cane=test_puck.cane, position_in_cane=2)
        logged_in_client.patch(
            f"/api/list/pucks/grid-box/{test_box_a.id}/move/",
            data={"puck_id": other.id, "position_in_puck": 3},
            content_type="application/json",
        )

        (entry,) = moved_via(timeline(logged_in_client, test_grid.id), "box")
        assert entry["summary"] == "Box moved: PuckA slot 1 to PuckB slot 3"
        assert entry["user"] == test_user.username

    def test_box_move_after_grid_left(self, logged_in_client, test_grid, test_box_a, test_box_b, test_puck):
        test_grid.grid_box = test_box_b
        test_grid.save()
        test_box_a.position_in_puck = 5
        test_box_a.save()

        assert moved_via(timeline(logged_in_client, test_grid.id), "box") == []

    # Saved directly, without a reason: the move is read from the diff
    @pytest.mark.parametrize(
        ("via", "field", "value", "summary"),
        [
            ("puck", "position_in_cane", lambda: 4, "Puck moved: same cane, position 1 to 4"),
            ("cane", "position_in_dewar", lambda: 3, "Cane moved: same dewar, slot 1 to 3"),
            ("dewar", "site", lambda: Site.objects.create(name="SiteB"), "Dewar moved: SiteA to SiteB"),
        ],
    )
    def test_container_move(self, logged_in_client, test_grid, test_puck, via, field, value, summary):
        container = {"puck": test_puck, "cane": test_puck.cane, "dewar": test_puck.cane.dewar}[via]
        setattr(container, field, value())
        container.save()

        (entry,) = moved_via(timeline(logged_in_client, test_grid.id), via)
        assert entry["summary"] == summary

    def test_puck_move_after_grid_left(self, logged_in_client, test_grid, test_puck, test_box_b):
        other_puck = Puck.objects.create(name="PuckB", cane=test_puck.cane, position_in_cane=2)
        test_box_b.puck = other_puck
        test_box_b.save()
        test_grid.grid_box = test_box_b
        test_grid.save()

        test_puck.position_in_cane = 6
        test_puck.save()

        assert moved_via(timeline(logged_in_client, test_grid.id), "puck") == []


@pytest.mark.django_db
class TestMsiSessionsAndProcRuns:
    def test_included(self, logged_in_client, test_grid, test_msi_session, test_proc_plan):
        test_msi_session.grid = test_grid
        test_msi_session.save()
        run = ProcRun.objects.create(name="run001", proc_plan=test_proc_plan, msi_session=test_msi_session)

        entries = timeline(logged_in_client, test_grid.id)
        subjects = {(e["subject"], e["subject_id"]) for e in entries}

        assert (Subject.MSI_SESSION, test_msi_session.id) in subjects
        assert (Subject.PROC_RUN, run.id) in subjects
