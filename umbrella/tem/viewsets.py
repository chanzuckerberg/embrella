"""
DRF ViewSets for the tem app.

- **session-overview** -- a denormalized read model backing the session
  browser at /sessions/browse: one row per MsiSession with its ProcRuns
  nested for table expansion.
"""

from django.db.models import (
    Case,
    CharField,
    Count,
    DateTimeField,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, NullIf, Substr
from drf_spectacular.utils import extend_schema, extend_schema_view
from processes.models import ProcRun, Review
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from umbrella.table_api import EntityTablePagination, TableQueryFilter, build_filters, value_counts

from common.sorting import MONTHS
from tem.models import MsiSession, SessionPlan
from tem.serializers import MsiSessionOverviewSerializer

# ProcRun rows for one session, reused by every per-session aggregate below.
_SESSION_RUNS = ProcRun.objects.filter(msi_session=OuterRef("pk")).order_by().values("msi_session")

# Chronological sort key for the Name column, in SQL: <yy><mm><dd><seq> from the name minus
# its prefix, so 26feb05b < 26apr15a and s26sep01a sits beside 26sep01a. Names off the
# scheme get a "~" key, which sorts after every digit.
#
#   name       s26apr15a
#   name_body  26apr15a      leading letters dropped, whatever the plan says
#   name_mon   apr           -> "04"
#   name_sort  26 04 15 a    -> "260415a"
#
# The prefix is read off the name, not the plan: sessions predate the field, and names are
# free text. `__regex` runs on both sqlite and MariaDB; one branch per prefix length up to
# SessionPlan.name_prefix's max_length.
_NAME_BODY = Case(
    *[
        When(name__regex=r"^[a-z]{%d}\d" % length, then=Substr("name", length + 1))
        for length in range(1, SessionPlan._meta.get_field("name_prefix").max_length + 1)
    ],
    default=F("name"),
    output_field=CharField(),
)
_MONTH_NUMBER = Case(
    *[When(name_mon=mon, then=Value("%02d" % number)) for number, mon in enumerate(MONTHS, start=1)],
    default=Value(""),
    output_field=CharField(),
)
_NAME_SORT = Case(
    When(
        name_mon__in=MONTHS,
        then=Concat(
            Substr("name_body", 1, 2),
            _MONTH_NUMBER,
            Substr("name_body", 6, 2),
            Substr("name_body", 8),
            output_field=CharField(),
        ),
    ),
    default=Concat(Value("~"), F("name"), output_field=CharField()),
    output_field=CharField(),
)

_PLAN_LABEL = Coalesce(NullIf("proc_plan__display_name", Value("")), "proc_plan__name")


def _processing_software_q(labels) -> Q:
    """
    Match sessions with a run whose plan label is in ``labels``.
    """
    return Q(procrun__proc_plan__display_name__in=labels) | Q(
        procrun__proc_plan__display_name="",
        procrun__proc_plan__name__in=labels,
    )


@extend_schema_view(
    list=extend_schema(
        tags=["TEM Sessions"],
        summary="List sessions with their processing runs",
        description=(
            "Paginated TEM sessions, each with its processing runs nested under `runs` "
            "for table expansion. Backs the session browser at /sessions/browse.\n\n"
            "**Reading the payload**\n\n"
            "- `pagination.totalResults` is the row count.\n"
            "- Runs carry `planName` (machine key, e.g. `czii-live`) *and* `planLabel` "
            "(display).\n"
            "- `user` is who created the session record."
        ),
    ),
    retrieve=extend_schema(
        tags=["TEM Sessions"],
        summary="Get one session overview row",
        description=("The same row shape as `list`, returned on its own -- no `result`/`pagination`/`sortBy` wrapper."),
    ),
)
class MsiSessionOverviewViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only session rows with nested runs, for the session browser table."""

    serializer_class = MsiSessionOverviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = EntityTablePagination
    filter_backends = [TableQueryFilter]

    table_filters = {
        "project": "project__name__in",
        "user": "user__username__in",
        "scope": "session_plan__scope__name__in",
        "workflow": "session_plan__imaging_workflow__workflow__in",
        # Traverses a to-many, so TableQueryFilter applies distinct().
        "processingSoftware": _processing_software_q,
    }
    table_search_fields = ["name", "project__name", "user__username", "grid__name"]
    table_sort_fields = {
        "name": "name_sort",
        "sessionDate": "created_at",
        "user": "user__username",
        "project": "project__name",
        "scope": "session_plan__scope__name",
        "workflow": "session_plan__imaging_workflow__workflow",
        "grid": "grid__name",
        "runCount": "run_count",
        "processingSoftware": "processing_software_sort",
        "reviewCount": "review_count",
        "lastRunAt": "last_run_at",
    }
    table_default_sort = ("sessionDate", False)
    table_tiebreak = "-pk"

    def get_queryset(self):
        """
        Aggregates with Subquery
        """
        return (
            MsiSession.objects.select_related(
                "user",
                "project",
                "grid",
                "session_plan__scope",
                "session_plan__imaging_workflow",
            )
            .prefetch_related(
                Prefetch(
                    "procrun_set",
                    queryset=ProcRun.objects.select_related("proc_plan").order_by("-created_at", "-id"),
                    to_attr="overview_runs",
                ),
            )
            .annotate(
                name_body=_NAME_BODY,
                run_count=Coalesce(
                    Subquery(
                        _SESSION_RUNS.annotate(n=Count("id")).values("n")[:1],
                        output_field=IntegerField(),
                    ),
                    0,
                ),
                last_run_at=Subquery(
                    _SESSION_RUNS.annotate(m=Max("created_at")).values("m")[:1],
                    output_field=DateTimeField(),
                ),
                review_count=Coalesce(
                    Subquery(
                        # Review's reverse accessor is `raw_tomograms`
                        Review.objects.filter(msi_session=OuterRef("pk"))
                        .order_by()
                        .values("msi_session")
                        .annotate(n=Count("pk"))
                        .values("n")[:1],
                        output_field=IntegerField(),
                    ),
                    0,
                ),
                # Sort key for `processingSoftware`: by alphabetical order of plan labels
                processing_software_sort=Coalesce(
                    Subquery(
                        _SESSION_RUNS.annotate(m=Min(_PLAN_LABEL)).values("m")[:1],
                        output_field=CharField(),
                    ),
                    Value(""),
                ),
            )
            # Chained: each step reads the annotation before it.
            .annotate(name_mon=Substr("name_body", 3, 3))
            .annotate(name_sort=_NAME_SORT)
        )

    @extend_schema(
        tags=["TEM Sessions"],
        summary="Filter options for the session browser sidebar",
        description=(
            "Available values for each filter category, with the number of sessions behind each. "
            "Counts are totals and ignore the active filters; the `q` param only decides which "
            "options come back marked `selected`."
        ),
    )
    @action(detail=False, methods=["get"])
    def filterlist(self, request):
        """Sidebar filter options. Categories mirror `table_filters`."""
        sessions = MsiSession.objects.all()

        return Response(
            {
                "filters": build_filters(
                    request,
                    {
                        "project": value_counts(sessions, "project__name"),
                        "user": value_counts(sessions, "user__username"),
                        "scope": value_counts(sessions, "session_plan__scope__name"),
                        "workflow": value_counts(sessions, "session_plan__imaging_workflow__workflow"),
                        "processingSoftware": value_counts(
                            ProcRun.objects.all(),
                            _PLAN_LABEL,
                            count="msi_session",
                        ),
                    },
                ),
            },
        )
