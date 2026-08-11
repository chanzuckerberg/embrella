"""
DRF ViewSets for the tem app.

- **session-overview** -- a denormalized read model backing the session
  browser at /sessions/browse: one row per MsiSession with its ProcRuns
  nested for table expansion.
"""

from django.db.models import (
    CharField,
    Count,
    DateTimeField,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce, NullIf
from drf_spectacular.utils import extend_schema, extend_schema_view
from processes.models import ProcRun, Review
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from umbrella.table_api import EntityTablePagination, TableQueryFilter, build_filters, value_counts

from tem.models import MsiSession
from tem.serializers import MsiSessionOverviewSerializer

# ProcRun rows for one session, reused by every per-session aggregate below.
_SESSION_RUNS = ProcRun.objects.filter(msi_session=OuterRef("pk")).order_by().values("msi_session")

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
        "name": "name",
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
