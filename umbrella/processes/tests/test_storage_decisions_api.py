"""
Endpoint tests for the storage-decisions API.

Recording a decision writes to StorageDecision and nothing else. Nothing in this
feature deletes, moves or modifies a file, and nothing here asserts that it does
-- `status: "delete"` is a human judgement that a directory looks reclaimable.
"""

import json

import pytest
from rest_framework.test import APIClient
from stores.models import Cluster
from tem.models import MsiSession

from processes.models import DirectorySummary, FilesystemSurvey, ProcSoftware, StorageDecision
from processes.services.storage_tree import build_storage_tree

URL = "/processes/v1/storage-decisions/"
SESSIONS_URL = "/processes/v1/storage-sessions/"
BASE = "/hpc/projects/group.czii/krios1.processing"


@pytest.fixture
def auth_client(db, django_user_model):
    client = APIClient()
    user = django_user_model.objects.create_user(username="decider", password="pw")
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture
def software(db):
    ProcSoftware.objects.all().delete()
    for name in ["aretomo3", "denoise"]:
        ProcSoftware.objects.create(
            name=name,
            version="test",
            storage_dirname=name,
        )
    return ProcSoftware.objects.all()


@pytest.fixture
def survey(software, session_plan, db):
    """
    One czii survey shaped like the real ones: a session spanning two software
    folders, which is the case a session-level decision has to handle.
    """
    Cluster.objects.get_or_create(cluster_id="czii", defaults={"name": "CZII"})
    fs = FilesystemSurvey.objects.create(
        cluster="czii",
        base_path=f"{BASE}/",
        status="completed",
        completed_at="2026-08-01T00:00:00Z",
    )
    MsiSession.objects.create(name="26mar02a", session_plan=session_plan)

    for path, size in [
        (f"{BASE}/aretomo3/26mar02a/run001", 300),
        (f"{BASE}/aretomo3/26mar02a/run002", 200),
        (f"{BASE}/denoise/26mar02a/run001", 500),
        (f"{BASE}/aretomo3/24oct24a/run001", 900),
    ]:
        relative = path[len(BASE) :].strip("/")
        DirectorySummary.objects.create(
            survey=fs,
            cluster="czii",
            path=path,
            depth=len(relative.split("/")),
            total_size_bytes=size,
            file_count=10,
            owner_username="alice",
            newest_file_mtime="2026-07-01T00:00:00Z",
            oldest_file_mtime="2026-06-01T00:00:00Z",
        )

    build_storage_tree(fs)
    return fs


def statuses(auth_client):
    """
    `software/session/run` -> effective status, as the table renders it.

    Keyed on the whole path, not on (software, run): run001 exists under both
    26mar02a and 24oct24a, so anything shorter silently collides and the last
    session read wins.
    """
    rows = auth_client.get(SESSIONS_URL, {"cluster": "czii"}).json()["result"]
    return {run["pathPrefix"][len(BASE) + 1 :]: run["status"] for row in rows for run in row["runs"]}


def session_status(auth_client, name):
    rows = auth_client.get(SESSIONS_URL, {"cluster": "czii"}).json()["result"]
    return next(row["status"] for row in rows if row["sessionName"] == name)


@pytest.mark.django_db
class TestAuth:
    def test_unauthenticated_post_is_rejected(self, survey):
        response = APIClient().post(
            URL,
            {"cluster": "czii", "path_prefixes": ["/x"], "status": "delete"},
            format="json",
            HTTP_ACCEPT="application/json",
        )

        assert response.status_code == 401
        assert StorageDecision.objects.count() == 0


@pytest.mark.django_db
class TestRecording:
    def test_run_level_decision_applies_to_that_run_only(self, auth_client, survey):
        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a/run001"], "status": "delete"},
            format="json",
        )

        assert response.status_code == 200
        effective = statuses(auth_client)
        assert effective["aretomo3/26mar02a/run001"] == "delete"
        assert effective["aretomo3/26mar02a/run002"] == "unset"
        # The same run name under a different session must be untouched.
        assert effective["aretomo3/24oct24a/run001"] == "unset"

    def test_session_decision_spans_every_software_folder(self, auth_client, survey):
        """
        The reason the endpoint takes a list: one judgement, several prefixes.
        """
        response = auth_client.post(
            URL,
            {
                "cluster": "czii",
                "path_prefixes": [f"{BASE}/aretomo3/26mar02a", f"{BASE}/denoise/26mar02a"],
                "status": "delete",
            },
            format="json",
        )

        assert response.status_code == 200
        assert len(response.json()["result"]) == 2

        effective = statuses(auth_client)
        assert effective["aretomo3/26mar02a/run001"] == "delete"
        assert effective["aretomo3/26mar02a/run002"] == "delete"
        assert effective["denoise/26mar02a/run001"] == "delete"
        # A different session is untouched.
        assert effective["aretomo3/24oct24a/run001"] == "unset"
        assert session_status(auth_client, "26mar02a") == "delete"
        assert session_status(auth_client, "24oct24a") == "unset"

    def test_decided_by_is_the_request_user_not_the_payload(self, auth_client, survey, django_user_model):
        other = django_user_model.objects.create_user(username="someone-else", password="pw")

        auth_client.post(
            URL,
            {
                "cluster": "czii",
                "path_prefixes": [f"{BASE}/aretomo3/26mar02a"],
                "status": "preserve",
                "decided_by": other.pk,
                "decidedBy": other.username,
            },
            format="json",
        )

        assert StorageDecision.objects.get().decided_by == auth_client.user

    def test_re_deciding_updates_rather_than_duplicating(self, auth_client, survey):
        prefix = f"{BASE}/aretomo3/26mar02a"
        for status in ("delete", "review", "preserve"):
            auth_client.post(
                URL,
                {"cluster": "czii", "path_prefixes": [prefix], "status": status, "notes": status},
                format="json",
            )

        row = StorageDecision.objects.get()
        assert row.status == "preserve"
        assert row.notes == "preserve"

    def test_notes_are_optional(self, auth_client, survey):
        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a"], "status": "review"},
            format="json",
        )

        assert response.status_code == 200
        assert StorageDecision.objects.get().notes == ""


@pytest.mark.django_db
class TestOverrideAndClear:
    def test_run_level_decision_overrides_its_session_parent(self, auth_client, survey):
        auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a"], "status": "delete"},
            format="json",
        )
        auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a/run002"], "status": "preserve"},
            format="json",
        )

        effective = statuses(auth_client)
        # Longest prefix wins.
        assert effective["aretomo3/26mar02a/run001"] == "delete"
        assert effective["aretomo3/26mar02a/run002"] == "preserve"
        assert session_status(auth_client, "26mar02a") == "mixed"

    def test_unset_deletes_the_row_and_reverts_to_inherited(self, auth_client, survey):
        auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a"], "status": "delete"},
            format="json",
        )
        auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a/run002"], "status": "preserve"},
            format="json",
        )

        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a/run002"], "status": "unset"},
            format="json",
        )

        assert response.json()["cleared"] == 1
        # The word "unset" is never stored -- the row is gone.
        assert StorageDecision.objects.filter(path_prefix__endswith="run002").count() == 0
        # ...and the run falls back to the session's decision, not to unset.
        assert statuses(auth_client)["aretomo3/26mar02a/run002"] == "delete"

    def test_clearing_a_session_clears_every_prefix(self, auth_client, survey):
        prefixes = [f"{BASE}/aretomo3/26mar02a", f"{BASE}/denoise/26mar02a"]
        auth_client.post(URL, {"cluster": "czii", "path_prefixes": prefixes, "status": "delete"}, format="json")

        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": prefixes, "status": "unset"},
            format="json",
        )

        assert response.json()["cleared"] == 2
        assert StorageDecision.objects.count() == 0
        assert session_status(auth_client, "26mar02a") == "unset"

    def test_inherited_status_reports_where_it_came_from(self, auth_client, survey):
        auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a"], "status": "delete"},
            format="json",
        )

        rows = auth_client.get(SESSIONS_URL, {"cluster": "czii"}).json()["result"]
        run = next(r for row in rows for r in row["runs"] if r["pathPrefix"] == f"{BASE}/aretomo3/26mar02a/run001")

        # Shorter than the row's own path, so the UI can say it is inherited and
        # offer to clear the parent rather than silently writing a second row.
        assert run["decidedAtPrefix"] == f"{BASE}/aretomo3/26mar02a"
        assert run["decidedAtPrefix"] != run["pathPrefix"]


@pytest.mark.django_db
class TestValidation:
    def test_prefix_outside_any_surveyed_root_is_rejected(self, auth_client, survey):
        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": ["/etc/passwd"], "status": "delete"},
            format="json",
        )

        assert response.status_code == 400
        assert "not under a surveyed directory" in str(response.json())
        assert StorageDecision.objects.count() == 0

    def test_relative_path_is_rejected(self, auth_client, survey):
        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": ["aretomo3/26mar02a"], "status": "delete"},
            format="json",
        )

        assert response.status_code == 400
        assert "absolute" in str(response.json())

    def test_prefix_matching_no_directory_is_rejected(self, auth_client, survey):
        """
        A decision about a path that is not on disk is invisible in the UI and
        cannot be cleared, so it has to fail at write time.
        """
        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/does-not-exist"], "status": "delete"},
            format="json",
        )

        assert response.status_code == 400
        assert "matches no directory" in str(response.json())

    def test_partial_failure_writes_nothing(self, auth_client, survey):
        """
        Atomicity is the point of taking a list: a half-applied session decision
        would read as 'mixed', which nobody chose.
        """
        response = auth_client.post(
            URL,
            {
                "cluster": "czii",
                "path_prefixes": [f"{BASE}/aretomo3/26mar02a", f"{BASE}/aretomo3/nonsense"],
                "status": "delete",
            },
            format="json",
        )

        assert response.status_code == 400
        assert StorageDecision.objects.count() == 0

    def test_unknown_cluster_is_rejected(self, auth_client, survey):
        response = auth_client.post(
            URL,
            {"cluster": "czi", "path_prefixes": [f"{BASE}/aretomo3/26mar02a"], "status": "delete"},
            format="json",
        )

        assert response.status_code == 400
        assert "Unknown cluster" in str(response.json())

    def test_empty_prefix_list_is_rejected(self, auth_client, survey):
        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [], "status": "delete"},
            format="json",
        )

        assert response.status_code == 400

    def test_prefix_matching_respects_directory_boundaries(self, auth_client, survey):
        """
        `.../run1` must not be treated as covering `.../run10`.
        """
        response = auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a/run00"], "status": "delete"},
            format="json",
        )

        assert response.status_code == 400
        assert "matches no directory" in str(response.json())


@pytest.mark.django_db
class TestDurability:
    def test_a_decision_survives_a_new_survey(self, auth_client, survey, software):
        """
        The property that motivated keying on the path instead of on a snapshot:
        a decision recorded against one survey still resolves after the next one
        lands with entirely new DirectorySummary rows.
        """
        auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a"], "status": "delete"},
            format="json",
        )

        newer = FilesystemSurvey.objects.create(
            cluster="czii",
            base_path=f"{BASE}/",
            status="completed",
            completed_at="2026-09-01T00:00:00Z",
        )
        for path in [f"{BASE}/aretomo3/26mar02a/run001", f"{BASE}/aretomo3/26mar02a/run003"]:
            DirectorySummary.objects.create(
                survey=newer,
                cluster="czii",
                path=path,
                depth=3,
                total_size_bytes=42,
                file_count=1,
                owner_username="alice",
            )
        build_storage_tree(newer)

        effective = statuses(auth_client)
        # Both the surviving run and one that did not exist when the call was made.
        assert effective["aretomo3/26mar02a/run001"] == "delete"
        assert effective["aretomo3/26mar02a/run003"] == "delete"


def record(auth_client, prefixes, status="delete", notes=""):
    response = auth_client.post(
        URL,
        {"cluster": "czii", "path_prefixes": prefixes, "status": status, "notes": notes},
        format="json",
    )
    assert response.status_code == 200, response.json()


def listing(auth_client, items=None, cluster="czii"):
    params = {"cluster": cluster}
    if items is not None:
        params["q"] = json.dumps(items)
    return auth_client.get(URL, params).json()


@pytest.mark.django_db
class TestListing:
    """
    The list endpoint speaks the shared `q` protocol: without pagination it
    would hand back every decision on a cluster in one response.
    """

    def test_envelope_shape(self, auth_client, survey):
        record(auth_client, [f"{BASE}/aretomo3/26mar02a"])

        body = listing(auth_client)

        assert set(body) == {"result", "pagination", "sortBy"}
        assert set(body["pagination"]) == {"page", "pageSize", "totalPages", "totalResults"}
        assert body["sortBy"] == {"sort": "decidedAt", "asc": False}

    def test_row_shape(self, auth_client, survey):
        record(auth_client, [f"{BASE}/aretomo3/26mar02a"], notes="old")

        row = listing(auth_client)["result"][0]

        assert set(row) == {"id", "cluster", "pathPrefix", "status", "notes", "decidedBy", "decidedAt"}
        assert row["decidedBy"] == "decider"

    def test_filters_by_cluster(self, auth_client, survey):
        record(auth_client, [f"{BASE}/aretomo3/26mar02a"])

        assert listing(auth_client)["pagination"]["totalResults"] == 1
        assert listing(auth_client, cluster="bruno")["result"] == []

    def test_paginates(self, auth_client, survey):
        """
        Seven rows, not three: the shared paginator keeps `orphans=3`, so a
        trailing part-page that small is absorbed into the one before it.
        """
        record(
            auth_client,
            [
                f"{BASE}/aretomo3/26mar02a",
                f"{BASE}/aretomo3/26mar02a/run001",
                f"{BASE}/aretomo3/26mar02a/run002",
                f"{BASE}/denoise/26mar02a",
                f"{BASE}/denoise/26mar02a/run001",
                f"{BASE}/aretomo3/24oct24a",
                f"{BASE}/aretomo3/24oct24a/run001",
            ],
        )

        body = listing(auth_client, [{"category": "pageSize", "value": [2]}])

        assert len(body["result"]) == 2
        assert body["pagination"]["totalResults"] == 7
        assert body["pagination"]["pageSize"] == 2

    def test_filters_by_session_without_a_stored_column(self, auth_client, survey):
        """
        The session is already in the path, so it is matched there.
        """
        record(auth_client, [f"{BASE}/aretomo3/26mar02a", f"{BASE}/denoise/26mar02a"])
        record(auth_client, [f"{BASE}/aretomo3/24oct24a"], status="preserve")

        body = listing(auth_client, [{"category": "session", "value": ["26mar02a"]}])

        assert body["pagination"]["totalResults"] == 2
        assert all("26mar02a" in row["pathPrefix"] for row in body["result"])

    def test_session_filter_matches_a_run_level_decision_too(self, auth_client, survey):
        record(auth_client, [f"{BASE}/aretomo3/26mar02a/run001"])

        body = listing(auth_client, [{"category": "session", "value": ["26mar02a"]}])

        assert [row["pathPrefix"] for row in body["result"]] == [f"{BASE}/aretomo3/26mar02a/run001"]

    def test_session_filter_respects_directory_boundaries(self, auth_client, survey):
        """
        A prefix of a session name must not match it.
        """
        record(auth_client, [f"{BASE}/aretomo3/26mar02a"])

        assert listing(auth_client, [{"category": "session", "value": ["26mar02"]}])["result"] == []

    def test_filters_by_status(self, auth_client, survey):
        record(auth_client, [f"{BASE}/aretomo3/26mar02a"], status="delete")
        record(auth_client, [f"{BASE}/aretomo3/24oct24a"], status="preserve")

        body = listing(auth_client, [{"category": "status", "value": ["preserve"]}])

        assert [row["status"] for row in body["result"]] == ["preserve"]

    def test_search_matches_the_path_and_the_notes(self, auth_client, survey):
        record(auth_client, [f"{BASE}/aretomo3/26mar02a"], notes="superseded by run003")
        record(auth_client, [f"{BASE}/denoise/26mar02a"], notes="")

        assert (
            listing(auth_client, [{"category": "search", "value": ["superseded"]}])["pagination"]["totalResults"] == 1
        )
        assert listing(auth_client, [{"category": "search", "value": ["denoise"]}])["pagination"]["totalResults"] == 1

    def test_sorts_by_path(self, auth_client, survey):
        record(auth_client, [f"{BASE}/denoise/26mar02a", f"{BASE}/aretomo3/26mar02a"])

        body = listing(auth_client, [{"category": "sort", "value": ["path"]}, {"category": "asc", "value": [True]}])

        assert [row["pathPrefix"] for row in body["result"]] == [
            f"{BASE}/aretomo3/26mar02a",
            f"{BASE}/denoise/26mar02a",
        ]


@pytest.mark.django_db
class TestDestroy:
    def test_destroy_removes_one(self, auth_client, survey):
        auth_client.post(
            URL,
            {"cluster": "czii", "path_prefixes": [f"{BASE}/aretomo3/26mar02a"], "status": "delete"},
            format="json",
        )
        row = StorageDecision.objects.get()

        assert auth_client.delete(f"{URL}{row.pk}/").status_code == 204
        assert StorageDecision.objects.count() == 0
