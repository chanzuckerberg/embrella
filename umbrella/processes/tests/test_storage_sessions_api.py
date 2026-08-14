"""
Endpoint tests for the storage-sessions API.
"""

import json

import pytest
from rest_framework.test import APIClient
from stores.models import Cluster
from tem.models import MsiSession

from processes.models import (
    DirectorySummary,
    FilesystemSurvey,
    ProcSoftware,
    StorageDecision,
    StorageRunSummary,
)
from processes.services.storage_tree import build_storage_tree

URL = "/processes/v1/storage-sessions/"
BASE = "/hpc/projects/group.czii/krios1.processing"


def q(items=None):
    """
    Query params: the `q` array encoded the way the frontend does, plus a cluster.

    The cluster is always named explicitly.
    """
    params = {"cluster": "czii"}
    if items is not None:
        params["q"] = json.dumps(items)
    return params


@pytest.fixture
def auth_client(db, django_user_model):
    client = APIClient()
    client.force_login(django_user_model.objects.create_user(username="tester", password="pw"))
    return client


@pytest.fixture
def software(db):
    ProcSoftware.objects.all().delete()
    for name in ["aretomo3", "denoise"]:
        ProcSoftware.objects.create(
            name=name,
            version="test",
            storage_dirname=name,
            script_directory=f"{BASE}/{name}/scripts",
        )
    return ProcSoftware.objects.all()


@pytest.fixture
def make_survey(db):
    def _make(cluster="czii", *, completed_at="2026-08-01T00:00:00Z", status="completed"):
        return FilesystemSurvey.objects.create(
            cluster=cluster,
            base_path=f"{BASE}/",
            status=status,
            completed_at=completed_at,
        )

    return _make


@pytest.fixture
def add_dir(db):
    def _add(survey, path, *, size=1000, files=10, owner="alice"):
        relative = path[len(BASE) :].strip("/")
        return DirectorySummary.objects.create(
            survey=survey,
            cluster=survey.cluster,
            path=path,
            depth=len(relative.split("/")),
            total_size_bytes=size,
            file_count=files,
            owner_username=owner,
            newest_file_mtime="2026-07-01T00:00:00Z",
            oldest_file_mtime="2026-06-01T00:00:00Z",
        )

    return _add


@pytest.fixture
def populated(software, make_survey, add_dir, session_plan):
    """
    One czii survey: a registered session across two software, and an
    unregistered one -- the shape the real surveys have.
    """
    survey = make_survey()
    MsiSession.objects.create(name="26mar02a", session_plan=session_plan)

    add_dir(survey, f"{BASE}/aretomo3/26mar02a/run001", size=300)
    add_dir(survey, f"{BASE}/aretomo3/26mar02a/run002", size=200)
    add_dir(survey, f"{BASE}/denoise/26mar02a/run001", size=500)
    add_dir(survey, f"{BASE}/aretomo3/20240308_002_Krios1_RP/run001", size=9000)

    build_storage_tree(survey)
    return survey


@pytest.mark.django_db
class TestAuth:
    def test_unauthenticated_returns_401(self):
        assert APIClient().get(URL, HTTP_ACCEPT="application/json").status_code == 401


@pytest.mark.django_db
class TestEnvelope:
    def test_envelope_shape(self, auth_client, populated):
        body = auth_client.get(URL, q()).json()

        assert set(body) == {"result", "pagination", "sortBy", "survey"}
        assert set(body["pagination"]) == {"page", "pageSize", "totalPages", "totalResults"}
        assert body["sortBy"] == {"sort": "size", "asc": False}

    def test_row_shape(self, auth_client, populated):
        row = auth_client.get(URL, q()).json()["result"][0]

        assert set(row) == {
            "storageSession",
            "sessionName",
            "registered",
            "msiSessionId",
            "user",
            "project",
            "fsOwner",
            "cluster",
            "softwareCount",
            "runCount",
            "directoryCount",
            "fileCount",
            "totalSizeBytes",
            "totalSizeDisplay",
            "lastModified",
            "status",
            "runs",
        }

    def test_run_shape(self, auth_client, populated):
        rows = auth_client.get(URL, q()).json()["result"]
        run = next(r for r in rows if r["sessionName"] == "26mar02a")["runs"][0]

        assert set(run) == {
            "id",
            "run",
            "software",
            "procRunId",
            "directoryCount",
            "fileCount",
            "totalSizeBytes",
            "totalSizeDisplay",
            "lastModified",
            "pathPrefix",
            "softwarePathPrefix",
            "status",
            "decidedAtPrefix",
        }
        # Namespaced so a run id cannot collide with a session row id.
        assert run["id"].startswith("storagerun-")

    def test_software_path_prefix_is_the_runs_parent(self, auth_client, populated):
        """
        The client records software- and session-tier decisions against this, so
        it has to be the run's parent directory and not the run itself.
        """
        rows = auth_client.get(URL, q()).json()["result"]
        runs = {
            (r["software"], r["run"]["name"]): r
            for r in next(x for x in rows if x["sessionName"] == "26mar02a")["runs"]
        }

        aretomo = runs[("aretomo3", "run001")]
        assert aretomo["pathPrefix"] == f"{BASE}/aretomo3/26mar02a/run001"
        assert aretomo["softwarePathPrefix"] == f"{BASE}/aretomo3/26mar02a"

        # Two software folders means two prefixes for one session.
        assert {r["softwarePathPrefix"] for r in runs.values()} == {
            f"{BASE}/aretomo3/26mar02a",
            f"{BASE}/denoise/26mar02a",
        }

    def test_biggest_session_is_first(self, auth_client, populated):
        rows = auth_client.get(URL, q()).json()["result"]

        # Default sort is size desc: the reclaim candidates are on page 1.
        assert [r["sessionName"] for r in rows] == ["20240308_002_Krios1_RP", "26mar02a"]


@pytest.mark.django_db
class TestRollup:
    def test_session_total_equals_sum_of_its_runs(self, auth_client, populated):
        rows = auth_client.get(URL, q()).json()["result"]

        for row in rows:
            assert row["totalSizeBytes"] == sum(run["totalSizeBytes"] for run in row["runs"])

    def test_session_spanning_two_software_is_one_row(self, auth_client, populated):
        row = next(r for r in auth_client.get(URL, q()).json()["result"] if r["sessionName"] == "26mar02a")

        assert row["softwareCount"] == 2
        assert row["runCount"] == 3
        assert row["totalSizeBytes"] == 1000
        assert sorted({run["software"] for run in row["runs"]}) == ["aretomo3", "denoise"]

    def test_unregistered_session_is_its_own_row(self, auth_client, populated):
        rows = {r["sessionName"]: r for r in auth_client.get(URL, q()).json()["result"]}

        orphan = rows["20240308_002_Krios1_RP"]
        assert orphan["registered"] is False
        assert orphan["msiSessionId"] is None
        assert orphan["user"] is None
        assert orphan["project"] is None
        # Still fully present -- on bruno this is the largest reclaim candidate.
        assert orphan["totalSizeBytes"] == 9000

        assert rows["26mar02a"]["registered"] is True


@pytest.mark.django_db
class TestSurveyResolution:
    def test_newest_completed_survey_is_used(self, auth_client, software, make_survey, add_dir):
        older = make_survey(completed_at="2026-01-01T00:00:00Z")
        newer = make_survey(completed_at="2026-08-01T00:00:00Z")
        add_dir(older, f"{BASE}/aretomo3/26mar02a/run001", size=111)
        add_dir(newer, f"{BASE}/aretomo3/26mar02a/run001", size=999)
        build_storage_tree(older)
        build_storage_tree(newer)

        body = auth_client.get(URL, q()).json()

        assert body["survey"]["id"] == newer.pk
        assert body["result"][0]["totalSizeBytes"] == 999

    def test_cluster_param_selects_the_cluster(self, auth_client, software, make_survey, add_dir):
        czii = make_survey("czii")
        bruno = make_survey("bruno")
        add_dir(czii, f"{BASE}/aretomo3/26mar02a/run001", size=100)
        add_dir(bruno, f"{BASE}/aretomo3/26aug09b/run001", size=700)
        build_storage_tree(czii)
        build_storage_tree(bruno)

        body = auth_client.get(URL, {"cluster": "bruno"}).json()

        assert body["survey"]["cluster"] == "bruno"
        assert [r["sessionName"] for r in body["result"]] == ["26aug09b"]

    def test_survey_block_reports_staleness(self, auth_client, populated):
        assert auth_client.get(URL, q()).json()["survey"]["stale"] is False

        # A survey touched after its tree was built: the numbers may no longer
        # match the directory rows.
        populated.save()

        assert auth_client.get(URL, q()).json()["survey"]["stale"] is True

    def test_known_cluster_with_no_completed_survey_is_empty_not_an_error(self, auth_client, software):
        """A real cluster nobody has surveyed yet is a legitimate empty state."""
        Cluster.objects.get_or_create(cluster_id="bruno", defaults={"name": "Bruno"})

        response = auth_client.get(URL, {"cluster": "bruno"})

        assert response.status_code == 200
        assert response.json()["result"] == []
        assert response.json()["survey"] is None

    def test_unknown_cluster_is_rejected(self, auth_client, software):
        """
        A typo in `?cluster=` must not look like "this cluster has no data".

        Returning an empty page makes the two indistinguishable, and the empty
        explorer reads as the latter.
        """
        response = auth_client.get(URL, {"cluster": "czi"})

        assert response.status_code == 400
        assert "Unknown cluster" in str(response.json()["cluster"])

    def test_missing_cluster_with_none_configured_is_rejected(self, auth_client, software):
        """No silent fallback to a hardcoded id."""
        Cluster.objects.all().delete()

        response = auth_client.get(URL)

        assert response.status_code == 400
        assert "No cluster is configured" in str(response.json()["cluster"])

    def test_cluster_defaults_to_the_configured_default(self, auth_client, software, make_survey, add_dir):
        Cluster.objects.all().delete()
        Cluster.objects.create(cluster_id="czii", name="CZII", is_default=True)
        survey = make_survey("czii")
        add_dir(survey, f"{BASE}/aretomo3/26mar02a/run001", size=42)
        build_storage_tree(survey)

        body = auth_client.get(URL).json()

        assert body["survey"]["cluster"] == "czii"
        assert body["result"][0]["totalSizeBytes"] == 42


@pytest.mark.django_db
class TestDecisions:
    def test_no_decision_reads_unset(self, auth_client, populated):
        row = next(r for r in auth_client.get(URL, q()).json()["result"] if r["sessionName"] == "26mar02a")

        assert row["status"] == "unset"
        assert all(run["status"] == "unset" for run in row["runs"])
        assert all(run["decidedAtPrefix"] is None for run in row["runs"])

    def test_session_level_decision_covers_every_run(self, auth_client, populated):
        StorageDecision.objects.create(
            cluster="czii",
            path_prefix=f"{BASE}/aretomo3/26mar02a",
            status="preserve",
        )

        row = next(r for r in auth_client.get(URL, q()).json()["result"] if r["sessionName"] == "26mar02a")
        aretomo_runs = [run for run in row["runs"] if run["software"] == "aretomo3"]
        denoise_runs = [run for run in row["runs"] if run["software"] == "denoise"]

        assert all(run["status"] == "preserve" for run in aretomo_runs)
        # Inherited, so the UI can say so rather than implying it was set here.
        assert all(run["decidedAtPrefix"] == f"{BASE}/aretomo3/26mar02a" for run in aretomo_runs)
        # A decision on the aretomo3 directory says nothing about denoise.
        assert all(run["status"] == "unset" for run in denoise_runs)

    def test_longest_prefix_wins(self, auth_client, populated):
        StorageDecision.objects.create(
            cluster="czii",
            path_prefix=f"{BASE}/aretomo3/26mar02a",
            status="preserve",
        )
        StorageDecision.objects.create(
            cluster="czii",
            path_prefix=f"{BASE}/aretomo3/26mar02a/run002",
            status="delete",
        )

        # Keyed by (software, run) -- run001 exists under both aretomo3 and
        # denoise, so the name alone is not unique within a session.
        runs = {
            (run["software"], run["run"]["name"]): run
            for r in auth_client.get(URL, q()).json()["result"]
            if r["sessionName"] == "26mar02a"
            for run in r["runs"]
        }

        assert runs[("aretomo3", "run001")]["status"] == "preserve"
        # The run-level decision overrides its session-level parent.
        assert runs[("aretomo3", "run002")]["status"] == "delete"
        assert runs[("aretomo3", "run002")]["decidedAtPrefix"] == f"{BASE}/aretomo3/26mar02a/run002"

    def test_session_status_is_mixed_when_runs_disagree(self, auth_client, populated):
        StorageDecision.objects.create(
            cluster="czii",
            path_prefix=f"{BASE}/aretomo3/26mar02a/run001",
            status="delete",
        )

        row = next(r for r in auth_client.get(URL, q()).json()["result"] if r["sessionName"] == "26mar02a")

        assert row["status"] == "mixed"

    def test_decision_on_another_cluster_does_not_apply(self, auth_client, populated):
        StorageDecision.objects.create(
            cluster="bruno",
            path_prefix=f"{BASE}/aretomo3/26mar02a",
            status="delete",
        )

        row = next(r for r in auth_client.get(URL, q()).json()["result"] if r["sessionName"] == "26mar02a")

        assert row["status"] == "unset"

    def test_prefix_matching_respects_directory_boundaries(self, auth_client, populated):
        """`run001` must not pick up a decision made on `run0011`."""
        StorageDecision.objects.create(
            cluster="czii",
            path_prefix=f"{BASE}/aretomo3/26mar02a/run0011",
            status="delete",
        )

        # Keyed by (software, run) -- run001 exists under both aretomo3 and
        # denoise, so the name alone is not unique within a session.
        runs = {
            (run["software"], run["run"]["name"]): run
            for r in auth_client.get(URL, q()).json()["result"]
            if r["sessionName"] == "26mar02a"
            for run in r["runs"]
        }

        assert runs[("aretomo3", "run001")]["status"] == "unset"


@pytest.mark.django_db
class TestFiltering:
    def test_software_filter_narrows_sizes_and_runs(self, auth_client, populated):
        """
        Deliberately unlike session-overview, which filters rows but not totals.

        Here the sizes are the point, so a row must equal the sum of the runs
        shown beneath it even under a filter.
        """
        body = auth_client.get(URL, q([{"category": "processingSoftware", "value": ["denoise"]}])).json()
        row = next(r for r in body["result"] if r["sessionName"] == "26mar02a")

        assert row["totalSizeBytes"] == 500
        assert [run["software"] for run in row["runs"]] == ["denoise"]
        assert row["totalSizeBytes"] == sum(run["totalSizeBytes"] for run in row["runs"])

    def test_session_filter_selects_one_row(self, auth_client, populated):
        body = auth_client.get(URL, q([{"category": "session", "value": ["26mar02a"]}])).json()

        assert [r["sessionName"] for r in body["result"]] == ["26mar02a"]

    def test_search_matches_session_name(self, auth_client, populated):
        body = auth_client.get(URL, q([{"category": "search", "value": ["20240308"]}])).json()

        assert [r["sessionName"] for r in body["result"]] == ["20240308_002_Krios1_RP"]

    def test_sort_by_session_name_ascending(self, auth_client, populated):
        body = auth_client.get(
            URL,
            q([{"category": "sort", "value": ["session"]}, {"category": "asc", "value": [True]}]),
        ).json()

        assert body["sortBy"] == {"sort": "session", "asc": True}
        assert [r["sessionName"] for r in body["result"]] == ["20240308_002_Krios1_RP", "26mar02a"]


@pytest.mark.django_db
class TestFilterlist:
    def test_shape_and_session_counts(self, auth_client, populated):
        body = auth_client.get(f"{URL}filterlist/", q()).json()

        assert set(body) == {"filters"}
        assert set(body["filters"]) == {"project", "user", "owner", "processingSoftware"}

        software = {option["name"]: option["count"] for option in body["filters"]["processingSoftware"]}
        # Counted in sessions, not directories: aretomo3 covers both sessions,
        # denoise only one.
        assert software == {"aretomo3": 2, "denoise": 1}

    def test_selected_reflects_the_q_param(self, auth_client, populated):
        body = auth_client.get(
            f"{URL}filterlist/",
            q([{"category": "processingSoftware", "value": ["denoise"]}]),
        ).json()

        selected = {option["name"]: option["selected"] for option in body["filters"]["processingSoftware"]}
        assert selected == {"aretomo3": False, "denoise": True}

    def test_counts_are_not_narrowed_by_the_selection(self, auth_client, populated):
        """Global counts, matching the filterlist actions elsewhere."""
        body = auth_client.get(
            f"{URL}filterlist/",
            q([{"category": "processingSoftware", "value": ["denoise"]}]),
        ).json()

        software = {option["name"]: option["count"] for option in body["filters"]["processingSoftware"]}
        assert software == {"aretomo3": 2, "denoise": 1}


@pytest.mark.django_db
class TestSummary:
    """
    The stats card's figures. `outsideTree` is the one worth guarding: it is a
    subtraction, so an error in either operand shows up as storage the view
    silently fails to account for.
    """

    def test_shape(self, auth_client, populated):
        body = auth_client.get(f"{URL}summary/", {"cluster": "czii"}).json()

        assert set(body) == {"survey", "total", "inTree", "outsideTree", "bySoftware"}
        assert set(body["total"]) == {"totalSizeBytes", "totalSizeDisplay", "directoryCount", "fileCount"}
        assert set(body["inTree"]) == {
            "totalSizeBytes",
            "totalSizeDisplay",
            "directoryCount",
            "fileCount",
            "sessionCount",
            "unregisteredSessionCount",
            "runCount",
        }
        assert body["survey"]["cluster"] == "czii"

    def test_in_tree_plus_outside_tree_equals_the_total(self, auth_client, populated, add_dir):
        """
        Every byte the survey saw lands in exactly one of the two tiles.
        """
        # relion is not Embrella software, so the tree must exclude it.
        add_dir(populated, f"{BASE}/relion/kagglePaper/run001", size=7777)

        body = auth_client.get(f"{URL}summary/", {"cluster": "czii"}).json()

        for key in ("totalSizeBytes", "directoryCount", "fileCount"):
            assert body["inTree"][key] + body["outsideTree"][key] == body["total"][key]

        # The excluded subtree is the whole of the difference here.
        assert body["outsideTree"]["totalSizeBytes"] == 7777
        assert body["outsideTree"]["directoryCount"] == 1

    def test_in_tree_totals_match_the_session_rows(self, auth_client, populated):
        summary = auth_client.get(f"{URL}summary/", {"cluster": "czii"}).json()
        rows = auth_client.get(URL, q()).json()["result"]

        assert summary["inTree"]["totalSizeBytes"] == sum(row["totalSizeBytes"] for row in rows)
        assert summary["inTree"]["sessionCount"] == len(rows)
        assert summary["inTree"]["unregisteredSessionCount"] == 1

    def test_by_software_is_largest_first_and_sums_to_the_tree(self, auth_client, populated):
        body = auth_client.get(f"{URL}summary/", {"cluster": "czii"}).json()

        sizes = [row["totalSizeBytes"] for row in body["bySoftware"]]
        assert sizes == sorted(sizes, reverse=True)
        assert sum(sizes) == body["inTree"]["totalSizeBytes"]

        by_name = {row["software"]: row for row in body["bySoftware"]}
        # Counted in sessions: aretomo3 holds both, denoise only one.
        assert by_name["aretomo3"]["sessionCount"] == 2
        assert by_name["denoise"]["sessionCount"] == 1

    def test_ignores_the_q_param(self, auth_client, populated):
        """
        A cluster snapshot, not a summary of the filtered page -- otherwise the
        card would restate the table instead of giving it context.
        """
        filtered = auth_client.get(
            f"{URL}summary/",
            {"cluster": "czii", "q": json.dumps([{"category": "processingSoftware", "value": ["denoise"]}])},
        ).json()
        unfiltered = auth_client.get(f"{URL}summary/", {"cluster": "czii"}).json()

        assert filtered == unfiltered

    def test_cluster_with_no_completed_survey_is_null_not_an_error(self, auth_client, software):
        Cluster.objects.get_or_create(cluster_id="bruno", defaults={"name": "Bruno"})
        response = auth_client.get(f"{URL}summary/", {"cluster": "bruno"})

        assert response.status_code == 200
        assert response.json() == {
            "survey": None,
            "total": None,
            "inTree": None,
            "outsideTree": None,
            "bySoftware": [],
        }

    def test_unknown_cluster_is_rejected(self, auth_client, populated):
        assert auth_client.get(f"{URL}summary/", {"cluster": "czi"}).status_code == 400


@pytest.mark.django_db
class TestScoping:
    def test_only_the_current_survey_is_read(self, auth_client, software, make_survey, add_dir):
        """
        The table holds one tree per survey, so an unscoped read would sum them.
        """
        older = make_survey(completed_at="2026-01-01T00:00:00Z")
        newer = make_survey(completed_at="2026-08-01T00:00:00Z")
        for survey in (older, newer):
            add_dir(survey, f"{BASE}/aretomo3/26mar02a/run001", size=100)
            build_storage_tree(survey)

        assert StorageRunSummary.objects.count() == 2

        body = auth_client.get(URL, q()).json()

        assert body["pagination"]["totalResults"] == 1
        assert body["result"][0]["totalSizeBytes"] == 100
