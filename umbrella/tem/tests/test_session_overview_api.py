"""Endpoint tests for the session-overview API."""

import json

import pytest
from django.contrib.auth.models import User
from django.urls import resolve
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from processes.models import ProcPlan, ProcRun, Review
from rest_framework.test import APIClient

from tem.models import MsiSession
from tem.viewsets import MsiSessionOverviewViewSet

URL = "/tem/v1/session-overview/"


def q(items):
    """Encode a `q` param the way the frontend does."""
    return {"q": json.dumps(items)}


@pytest.fixture
def auth_client(test_user):
    client = APIClient()
    client.force_login(test_user)
    return client


@pytest.fixture
def live_plan(db):
    return ProcPlan.objects.create(name="czii-live", display_name="aretomo3")


@pytest.fixture
def denoise_plan(db):
    return ProcPlan.objects.create(name="czii-denoise", display_name="denoise")


@pytest.fixture
def make_session(db, session_plan, project, grid, test_user):
    def _make(name, user=test_user, **kwargs):
        return MsiSession.objects.create(
            name=name,
            user=user,
            project=kwargs.pop("project", project),
            grid=kwargs.pop("grid", grid),
            session_plan=session_plan,
            **kwargs,
        )

    return _make


class TestRouting:
    def test_overview_resolves_to_the_viewset(self):
        assert resolve(URL).func.cls is MsiSessionOverviewViewSet

    def test_create_session_still_owns_the_bare_sessions_path(self):
        assert resolve("/tem/v1/sessions/").func is not MsiSessionOverviewViewSet


@pytest.mark.django_db
class TestAuth:
    def test_unauthenticated_returns_401(self):
        assert APIClient().get(URL, HTTP_ACCEPT="application/json").status_code == 401


@pytest.mark.django_db
class TestResponseShape:
    def test_response_wrapper_shape(self, auth_client, make_session):
        make_session("24mar01a")
        body = auth_client.get(URL).json()
        assert set(body) == {"result", "pagination", "sortBy"}
        assert set(body["pagination"]) == {"page", "pageSize", "totalPages", "totalResults"}
        assert set(body["sortBy"]) == {"sort", "asc"}
        assert body["sortBy"] == {"sort": "sessionDate", "asc": False}

    def test_row_shape(self, auth_client, make_session, live_plan, project, grid, test_user):
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=live_plan)

        row = auth_client.get(URL).json()["result"][0]

        assert set(row) == {
            "session",
            "sessionDate",
            "user",
            "project",
            "scope",
            "workflow",
            "grid",
            "runCount",
            "processingSoftware",
            "reviewCount",
            "lastRunAt",
            "runs",
        }
        assert row["session"] == {"id": session.pk, "name": "24mar01a"}
        assert row["user"] == {"id": test_user.pk, "username": "testuser", "fullName": "testuser"}
        assert row["project"] == {"id": project.pk, "name": "TestProject"}
        assert row["grid"] == {"id": grid.pk, "name": "TestGrid"}
        assert row["scope"] == "TestScope"
        assert row["workflow"] == "tomo"
        assert row["runCount"] == 1
        assert row["processingSoftware"] == ["aretomo3"]
        assert row["reviewCount"] == 0

    def test_nullable_fields_serialize_as_null(self, auth_client, make_session):
        make_session("24mar01a", user=None, project=None, grid=None)
        row = auth_client.get(URL).json()["result"][0]
        assert row["user"] is None
        assert row["project"] is None
        assert row["grid"] is None

    def test_user_full_name_uses_first_last_when_set(self, auth_client, make_session):
        named = User.objects.create_user(username="test.user@test.org", first_name="Test", last_name="User")
        make_session("24mar01a", user=named)
        assert auth_client.get(URL).json()["result"][0]["user"]["fullName"] == "Test User"

    def test_user_full_name_falls_back_to_domain_stripped_username(self, auth_client, make_session):
        bare = User.objects.create_user(username="test.user@test.org")
        make_session("24mar01a", user=bare)
        assert auth_client.get(URL).json()["result"][0]["user"]["fullName"] == "test.user"


@pytest.mark.django_db
class TestSubRows:
    def test_runs_nested_newest_first_with_namespaced_ids(self, auth_client, make_session, live_plan):
        session = make_session("24mar01a")
        first = ProcRun.objects.create(name="run001", msi_session=session, proc_plan=live_plan)
        second = ProcRun.objects.create(name="run002", msi_session=session, proc_plan=live_plan)

        runs = auth_client.get(URL).json()["result"][0]["runs"]

        assert [r["run"]["name"] for r in runs] == ["run002", "run001"]
        assert [r["id"] for r in runs] == [f"run-{second.pk}", f"run-{first.pk}"]
        assert set(runs[0]) == {"id", "run", "planName", "planLabel", "createdAt"}

    def test_plan_name_and_label_both_present_and_distinct(self, auth_client, make_session, live_plan):
        # Guards against "simplifying" the duplication away: ProcPlan.name
        # feeds path templates and literal comparisons, so it must survive
        # even though planLabel is what gets displayed.
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=live_plan)

        run = auth_client.get(URL).json()["result"][0]["runs"][0]
        assert run["planName"] == "czii-live"
        assert run["planLabel"] == "aretomo3"
        assert run["planName"] != run["planLabel"]

    def test_zero_run_session(self, auth_client, make_session):
        make_session("24mar01a")
        row = auth_client.get(URL).json()["result"][0]
        assert row["runs"] == []
        assert row["runCount"] == 0
        assert row["processingSoftware"] == []
        assert row["lastRunAt"] is None


@pytest.mark.django_db
class TestAggregates:
    def test_run_and_review_counts_do_not_inflate_each_other(self, auth_client, make_session, live_plan, test_user):
        session = make_session("24mar01a")
        for name in ("run001", "run002", "run003"):
            ProcRun.objects.create(name=name, msi_session=session, proc_plan=live_plan)
        for i in range(2):
            Review.objects.create(
                review_name=f"review{i}",
                review_type="manual",
                run_id="run001",
                reconstruction_type="DCTF",
                msi_session=session,
                requestor=test_user,
            )

        row = auth_client.get(URL).json()["result"][0]
        assert row["runCount"] == 3
        assert row["reviewCount"] == 2

    def test_processing_software_deduplicates_across_runs_on_one_plan(self, auth_client, make_session, live_plan):
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=live_plan)
        ProcRun.objects.create(name="run002", msi_session=session, proc_plan=live_plan)

        row = auth_client.get(URL).json()["result"][0]
        assert row["processingSoftware"] == ["aretomo3"]
        assert row["runCount"] == 2

    def test_processing_software_falls_back_to_plan_name_when_display_name_blank(self, auth_client, make_session):
        unlabeled = ProcPlan.objects.create(name="pytom-pick", display_name="")
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=unlabeled)

        assert auth_client.get(URL).json()["result"][0]["processingSoftware"] == ["pytom-pick"]

    def test_last_run_at_is_the_newest_run(self, auth_client, make_session, live_plan):
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=live_plan)
        newest = ProcRun.objects.create(name="run002", msi_session=session, proc_plan=live_plan)

        row = auth_client.get(URL).json()["result"][0]
        # Compare instants, not strings: DRF renders UTC while created_at is
        # in the active timezone.
        assert parse_datetime(row["lastRunAt"]) == newest.created_at


@pytest.mark.django_db
class TestSortingAndPaging:
    def test_sort_by_name_ascending(self, auth_client, make_session):
        for name in ("24mar03a", "24mar01a", "24mar02a"):
            make_session(name)

        body = auth_client.get(
            URL,
            q([{"category": "sort", "value": ["name"]}, {"category": "asc", "value": [True]}]),
        ).json()
        assert [r["session"]["name"] for r in body["result"]] == ["24mar01a", "24mar02a", "24mar03a"]
        assert body["sortBy"] == {"sort": "name", "asc": True}

    def test_sort_by_run_count_descending(self, auth_client, make_session, live_plan):
        few = make_session("24mar01a")
        many = make_session("24mar02a")
        ProcRun.objects.create(name="run001", msi_session=few, proc_plan=live_plan)
        for name in ("run001", "run002"):
            ProcRun.objects.create(name=name, msi_session=many, proc_plan=live_plan)

        body = auth_client.get(
            URL,
            q([{"category": "sort", "value": ["runCount"]}, {"category": "asc", "value": [False]}]),
        ).json()
        assert [r["session"]["name"] for r in body["result"]] == ["24mar02a", "24mar01a"]

    def test_sort_by_processing_software_uses_first_label_and_puts_runless_first(
        self, auth_client, make_session, live_plan, denoise_plan
    ):
        runless = make_session("24mar01a")  # noqa: F841 -- asserted by position below
        denoised = make_session("24mar02a")
        aretomo = make_session("24mar03a")
        ProcRun.objects.create(name="run001", msi_session=denoised, proc_plan=denoise_plan)
        ProcRun.objects.create(name="run001", msi_session=aretomo, proc_plan=live_plan)

        body = auth_client.get(
            URL,
            q([{"category": "sort", "value": ["processingSoftware"]}, {"category": "asc", "value": [True]}]),
        ).json()
        assert [r["processingSoftware"] for r in body["result"]] == [[], ["aretomo3"], ["denoise"]]

    def test_pagination_arithmetic(self, auth_client, make_session):
        # 9 rows at pageSize 2 gives 3 pages: ceil((9 - orphans) / 2). Fewer
        # rows and orphans=3 would fold everything onto one page.
        for i in range(9):
            make_session(f"24mar0{i}a")

        body = auth_client.get(
            URL,
            q([{"category": "pageSize", "value": [2]}, {"category": "page", "value": [2]}]),
        ).json()
        assert body["pagination"] == {"page": 2, "pageSize": 2, "totalPages": 3, "totalResults": 9}
        assert len(body["result"]) == 2

    def test_paging_is_stable_when_created_at_ties(self, auth_client, make_session):
        stamp = timezone.now()
        for i in range(9):
            make_session(f"24mar0{i}a", created_at=stamp)

        seen = []
        for page in (1, 2, 3):
            body = auth_client.get(
                URL,
                q([{"category": "pageSize", "value": [2]}, {"category": "page", "value": [page]}]),
            ).json()
            seen.extend(r["session"]["id"] for r in body["result"])

        # Without the -pk tiebreak, tied created_at lets rows repeat across
        # pages and others never appear.
        assert len(seen) == 9
        assert len(set(seen)) == 9

    def test_orphans_absorbs_the_tail_page(self, auth_client, make_session):
        for i in range(31):
            make_session(f"24mar{i:03d}a")

        body = auth_client.get(URL, q([{"category": "pageSize", "value": [28]}])).json()
        assert body["pagination"]["totalPages"] == 1
        assert body["pagination"]["totalResults"] == 31
        assert len(body["result"]) == 31


@pytest.mark.django_db
class TestFiltering:
    def test_filter_by_processing_software_matches_once_and_keeps_run_totals(
        self, auth_client, make_session, live_plan, denoise_plan
    ):
        matching = make_session("24mar01a")
        other = make_session("24mar02a")
        # Two runs on the filtered plan -- the session must appear once, and
        # its nested runs must still include the unfiltered denoise run.
        ProcRun.objects.create(name="run001", msi_session=matching, proc_plan=live_plan)
        ProcRun.objects.create(name="run002", msi_session=matching, proc_plan=live_plan)
        ProcRun.objects.create(name="run003", msi_session=matching, proc_plan=denoise_plan)
        ProcRun.objects.create(name="run001", msi_session=other, proc_plan=denoise_plan)

        body = auth_client.get(URL, q([{"category": "processingSoftware", "value": ["aretomo3"]}])).json()

        assert body["pagination"]["totalResults"] == 1
        assert len(body["result"]) == 1
        row = body["result"][0]
        assert row["session"]["name"] == "24mar01a"
        assert row["runCount"] == 3
        assert len(row["runs"]) == 3

    def test_search_matches_session_name(self, auth_client, make_session):
        make_session("24mar01a")
        make_session("25dec08a")

        body = auth_client.get(URL, q([{"category": "search", "value": ["24mar"]}])).json()
        assert [r["session"]["name"] for r in body["result"]] == ["24mar01a"]

    def test_unknown_filter_category_ignored(self, auth_client, make_session):
        make_session("24mar01a")
        body = auth_client.get(URL, q([{"category": "nonsense", "value": ["x"]}])).json()
        assert body["pagination"]["totalResults"] == 1

    def test_filter_by_processing_software_matches_plan_with_blank_display_name(self, auth_client, make_session):
        # The row renders `["pytom-pick"]` via ProcPlan.label, so that value has
        # to be filterable too -- otherwise the sidebar offers a dead option.
        unlabeled = ProcPlan.objects.create(name="pytom-pick", display_name="")
        matching = make_session("24mar01a")
        make_session("24mar02a")
        ProcRun.objects.create(name="run001", msi_session=matching, proc_plan=unlabeled)

        body = auth_client.get(URL, q([{"category": "processingSoftware", "value": ["pytom-pick"]}])).json()

        assert body["pagination"]["totalResults"] == 1
        assert body["result"][0]["session"]["name"] == "24mar01a"

    def test_filter_by_processing_software_does_not_duplicate_rows(
        self, auth_client, make_session, live_plan, denoise_plan
    ):
        # Two runs on the filtered plan means two join rows; the callable
        # filter still has to come back through TableQueryFilter's distinct().
        session = make_session("24mar01a")
        for name in ("run001", "run002"):
            ProcRun.objects.create(name=name, msi_session=session, proc_plan=live_plan)
        ProcRun.objects.create(name="run003", msi_session=session, proc_plan=denoise_plan)

        body = auth_client.get(URL, q([{"category": "processingSoftware", "value": ["aretomo3"]}])).json()

        assert body["pagination"]["totalResults"] == 1
        assert len(body["result"]) == 1


@pytest.mark.django_db
class TestFilterList:
    URL = f"{URL}filterlist/"

    def test_unauthenticated_returns_401(self):
        assert APIClient().get(self.URL, HTTP_ACCEPT="application/json").status_code == 401

    def test_returns_every_configured_category(self, auth_client, make_session):
        make_session("24mar01a")
        body = auth_client.get(self.URL).json()

        assert set(body) == {"filters"}
        assert set(body["filters"]) == {"project", "user", "scope", "workflow", "processingSoftware"}
        assert set(MsiSessionOverviewViewSet.table_filters) == set(body["filters"])

    def test_option_shape(self, auth_client, make_session):
        make_session("24mar01a")
        option = auth_client.get(self.URL).json()["filters"]["project"][0]
        assert option == {"name": "TestProject", "count": 1, "selected": False}

    def test_counts_sessions_not_runs(self, auth_client, make_session, live_plan):
        # Three runs on one plan is still one session behind the option.
        session = make_session("24mar01a")
        for name in ("run001", "run002", "run003"):
            ProcRun.objects.create(name=name, msi_session=session, proc_plan=live_plan)

        assert auth_client.get(self.URL).json()["filters"]["processingSoftware"] == [
            {"name": "aretomo3", "count": 1, "selected": False},
        ]

    def test_processing_software_lists_blank_display_name_plans_under_their_name(self, auth_client, make_session):
        unlabeled = ProcPlan.objects.create(name="pytom-pick", display_name="")
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=unlabeled)

        names = [o["name"] for o in auth_client.get(self.URL).json()["filters"]["processingSoftware"]]
        assert names == ["pytom-pick"]

    def test_options_are_sorted_and_deduplicated(self, auth_client, make_session, live_plan, denoise_plan):
        first = make_session("24mar01a")
        second = make_session("24mar02a")
        ProcRun.objects.create(name="run001", msi_session=first, proc_plan=denoise_plan)
        ProcRun.objects.create(name="run001", msi_session=second, proc_plan=live_plan)
        ProcRun.objects.create(name="run002", msi_session=second, proc_plan=denoise_plan)

        assert auth_client.get(self.URL).json()["filters"]["processingSoftware"] == [
            {"name": "aretomo3", "count": 1, "selected": False},
            {"name": "denoise", "count": 2, "selected": False},
        ]

    def test_null_project_is_not_offered_as_an_option(self, auth_client, make_session):
        make_session("24mar01a", project=None)
        assert auth_client.get(self.URL).json()["filters"]["project"] == []

    def test_selected_reflects_the_q_param(self, auth_client, make_session, live_plan, denoise_plan):
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=live_plan)
        ProcRun.objects.create(name="run002", msi_session=session, proc_plan=denoise_plan)

        filters = auth_client.get(
            self.URL,
            q([{"category": "processingSoftware", "value": ["denoise"]}]),
        ).json()["filters"]

        assert {o["name"]: o["selected"] for o in filters["processingSoftware"]} == {
            "aretomo3": False,
            "denoise": True,
        }

    def test_counts_ignore_the_active_filters(self, auth_client, make_session, live_plan, denoise_plan):
        # Counts are totals -- narrowing to one plan must not zero out the other
        # option, or the sidebar becomes a dead end.
        first = make_session("24mar01a")
        second = make_session("24mar02a")
        ProcRun.objects.create(name="run001", msi_session=first, proc_plan=live_plan)
        ProcRun.objects.create(name="run001", msi_session=second, proc_plan=denoise_plan)

        filters = auth_client.get(
            self.URL,
            q([{"category": "processingSoftware", "value": ["aretomo3"]}]),
        ).json()["filters"]

        assert {o["name"]: o["count"] for o in filters["processingSoftware"]} == {"aretomo3": 1, "denoise": 1}


@pytest.mark.django_db
class TestQueryBudget:
    def test_query_count_is_flat_in_row_count(self, auth_client, make_session, live_plan, django_assert_num_queries):
        for s in range(10):
            session = make_session(f"24mar{s:02d}a")
            for r in range(3):
                ProcRun.objects.create(name=f"run{r:03d}", msi_session=session, proc_plan=live_plan)
        with django_assert_num_queries(5):
            body = auth_client.get(URL).json()

        assert len(body["result"]) == 10
        assert all(len(row["runs"]) == 3 for row in body["result"])


@pytest.mark.django_db
class TestRetrieve:
    def test_retrieve_returns_bare_row_without_wrapper(self, auth_client, make_session, live_plan):
        session = make_session("24mar01a")
        ProcRun.objects.create(name="run001", msi_session=session, proc_plan=live_plan)

        body = auth_client.get(f"{URL}{session.pk}/").json()
        assert "result" not in body
        assert body["session"] == {"id": session.pk, "name": "24mar01a"}
        assert body["processingSoftware"] == ["aretomo3"]
