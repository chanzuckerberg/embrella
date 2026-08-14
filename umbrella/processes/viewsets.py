"""
DRF ViewSets for the processes app.

- **storage-sessions** -- storage rolled up per MSI session, backing the Storage
  Explorer. Reads the materialized StorageRunSummary tree
"""

from collections import defaultdict

from django.db import transaction
from django.db.models import Count, Max, Min, Q, Sum
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from stores.models import Cluster
from umbrella.table_api import EntityTablePagination, TableQueryFilter, build_filters, value_counts

from processes.models import (
    DirectorySummary,
    FilesystemSurvey,
    StorageDecision,
    StorageRunSummary,
    current_survey,
    format_bytes,
)
from processes.serializers import (
    StorageDecisionSerializer,
    StorageDecisionWriteSerializer,
    StorageSessionSerializer,
)
from processes.services.decisions import UNSET, decisions_for, effective_status, rollup_status, session_filter
from processes.services.storage_tree import tree_is_stale


class StorageSessionPagination(EntityTablePagination):
    page_size = 10

    def get_paginated_response_schema(self, schema):
        paginated = super().get_paginated_response_schema(schema)
        paginated["properties"]["survey"] = {
            "type": "object",
            "nullable": True,
            "description": "Which survey the figures came from. Null when the cluster has none completed.",
            "properties": {
                "id": {"type": "integer", "example": 6},
                "cluster": {"type": "string", "example": "czii"},
                "completedAt": {"type": "string", "format": "date-time", "nullable": True},
                "stale": {
                    "type": "boolean",
                    "description": "The survey changed after its tree was built; figures may be out of date.",
                },
            },
        }
        return paginated


def resolve_cluster(requested):
    """
    Cluster id for this request
    """
    known = set(Cluster.objects.values_list("cluster_id", flat=True))

    if requested:
        if requested not in known:
            raise ValidationError(
                {
                    "cluster": (
                        f"Unknown cluster {requested!r}. "
                        f"Known clusters: {', '.join(sorted(known)) or 'none configured'}."
                    ),
                },
            )
        return requested

    default = Cluster.get_default()
    if default is None:
        raise ValidationError(
            {
                "cluster": (
                    "No cluster is configured, so there is no default to fall back to. "
                    "Add a stores.Cluster (and mark one is_default), or pass ?cluster= explicitly."
                ),
            },
        )
    return default.cluster_id


def _size_block(size, directories, files):
    """
    The four figures every tile on the stats card shows.
    """
    return {
        "totalSizeBytes": size,
        "totalSizeDisplay": format_bytes(size),
        "directoryCount": directories,
        "fileCount": files,
    }


@extend_schema_view(
    list=extend_schema(
        tags=["Storage Explorer"],
        summary="List storage grouped by MSI session",
        description=(
            "Storage for one cluster, grouped per MSI session, with each session's run "
            "directories nested under `runs`.\n\n"
            "Reads the newest completed survey for `cluster` and reports which one in "
            "`survey`. Covers only directories under a known processing-software folder; "
            "anything else is visible via `/processes/v1/directories/`."
        ),
        parameters=[
            OpenApiParameter(
                name="cluster",
                description="Cluster id, e.g. czii or bruno. Defaults to the configured default cluster.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="survey_id",
                description="Pin a specific survey instead of the newest completed one.",
                required=False,
                type=int,
            ),
        ],
    ),
)
class StorageSessionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Read-only storage rollups per session, for the Storage Explorer table.
    """

    serializer_class = StorageSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StorageSessionPagination
    filter_backends = [TableQueryFilter]

    table_filters = {
        "project": "msi_session__project__name__in",
        "user": "msi_session__user__username__in",
        "owner": "owner_username__in",
        "processingSoftware": "software__in",
        "session": "session_name__in",
    }
    table_search_fields = ["session_name", "software", "run_name"]
    table_sort_fields = {
        "session": "session_name",
        "size": "total_size_bytes_sum",
        "directories": "directory_count_sum",
        "runs": "run_count",
        "lastModified": "last_modified",
        "project": "msi_session__project__name",
        "owner": "fs_owner",
        "user": "msi_session__user__username",
    }
    table_default_sort = ("size", False)
    table_tiebreak = "session_name"

    def _cluster(self):
        if not hasattr(self, "_resolved_cluster"):
            self._resolved_cluster = resolve_cluster(self.request.query_params.get("cluster"))
        return self._resolved_cluster

    def _survey(self):
        """
        Which survey this request reads.
        """
        if not hasattr(self, "_resolved_survey"):
            survey_id = self.request.query_params.get("survey_id")
            if survey_id:
                self._resolved_survey = FilesystemSurvey.objects.filter(pk=survey_id).first()
            else:
                self._resolved_survey = current_survey(self._cluster())
        return self._resolved_survey

    def _leaf_queryset(self):
        """Leaves for this request's survey, before grouping. Filters land here."""
        survey = self._survey()
        if survey is None:
            return StorageRunSummary.objects.none()
        return StorageRunSummary.objects.filter(survey=survey)

    def get_queryset(self):
        return (
            self._leaf_queryset()
            .values(
                "session_name",
                "cluster",
                "msi_session_id",
                "msi_session__project_id",
                "msi_session__project__name",
                "msi_session__user_id",
                "msi_session__user__username",
                "msi_session__user__first_name",
                "msi_session__user__last_name",
            )
            .annotate(
                total_size_bytes_sum=Sum("total_size_bytes"),
                directory_count_sum=Sum("directory_count"),
                file_count_sum=Sum("file_count"),
                # Leaves with an empty run_name are the session root, not a run.
                run_count=Count("id", filter=~Q(run_name="")),
                software_count=Count("software", distinct=True),
                last_modified=Max("newest_file_mtime"),
                first_modified=Min("oldest_file_mtime"),
                fs_owner=Max("owner_username"),
            )
        )

    def _rows_with_runs(self, page):
        """
        Turn aggregate rows into serializable dicts, each carrying its leaves.
        """
        session_names = [row["session_name"] for row in page]
        leaves_by_session = defaultdict(list)

        leaves = (
            TableQueryFilter()
            .filter_only(self.request, self._leaf_queryset(), self)
            .filter(session_name__in=session_names)
            .select_related("proc_run")
            .order_by("software", "run_name")
        )
        decisions = decisions_for(self._cluster())

        for leaf in leaves:
            status, decided_at = effective_status(leaf.path_prefix, decisions)
            leaf.status = status
            leaf.decided_at_prefix = decided_at
            leaves_by_session[leaf.session_name].append(leaf)

        rows = []
        for row in page:
            runs = leaves_by_session.get(row["session_name"], [])
            first = row["msi_session__user__first_name"] or ""
            last = row["msi_session__user__last_name"] or ""
            username = row["msi_session__user__username"] or ""
            rows.append(
                {
                    "session_name": row["session_name"],
                    "cluster": row["cluster"],
                    "registered": row["msi_session_id"] is not None,
                    "msi_session_id": row["msi_session_id"],
                    "user_id": row["msi_session__user_id"],
                    "username": username,
                    "user_full_name": f"{first} {last}".strip() or username.split("@")[0],
                    "project_id": row["msi_session__project_id"],
                    "project_name": row["msi_session__project__name"],
                    "fs_owner": row["fs_owner"] or "",
                    "software_count": row["software_count"],
                    "run_count": row["run_count"],
                    "directory_count": row["directory_count_sum"],
                    "file_count": row["file_count_sum"],
                    "total_size_bytes": row["total_size_bytes_sum"],
                    "last_modified": row["last_modified"],
                    "status": rollup_status(leaf.status for leaf in runs),
                    "runs": runs,
                },
            )
        return rows

    def _survey_block(self):
        """Which snapshot the numbers came from, so the UI can say 'as of ...'."""
        survey = self._survey()
        if survey is None:
            return None
        return {
            "id": survey.pk,
            "cluster": survey.cluster,
            "completedAt": survey.completed_at,
            "stale": tree_is_stale(survey),
        }

    def list(self, request, *args, **kwargs):
        """Paginate the aggregate, then attach each page row's leaves."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is None:
            serializer = self.get_serializer(self._rows_with_runs(list(queryset)), many=True)
            return Response({"result": serializer.data, "survey": self._survey_block()})

        serializer = self.get_serializer(self._rows_with_runs(page), many=True)
        response = self.get_paginated_response(serializer.data)
        response.data["survey"] = self._survey_block()
        return response

    @extend_schema(
        tags=["Storage Explorer"],
        summary="Cluster-wide storage totals for the explorer's stats card",
        description=(
            "One snapshot of the cluster, ignoring `q` entirely -- these are the figures the header "
            "card shows, not a summary of the current page.\n\n"
            "`total` covers every directory the survey recorded. `inTree` covers only those under a "
            "known processing-software folder, which is all the session table can show. "
            "`outsideTree` is the difference: `relion`, `warptools` and anything else the allowlist "
            "excludes, plus the software directories themselves. It is the one number that says how "
            "much of the cluster this view cannot account for, so it is worth reading before "
            "concluding the table shows everything."
        ),
        parameters=[
            OpenApiParameter(
                name="cluster",
                description="Cluster id. Defaults to the configured default cluster.",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "survey": {
                        "type": "object",
                        "nullable": True,
                        "description": "Null when the cluster has no completed survey; every other block is null too.",
                    },
                    "total": {"type": "object", "nullable": True},
                    "inTree": {"type": "object", "nullable": True},
                    "outsideTree": {"type": "object", "nullable": True},
                    "bySoftware": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        survey = self._survey()
        if survey is None:
            return Response(
                {"survey": None, "total": None, "inTree": None, "outsideTree": None, "bySoftware": []},
            )

        leaves = StorageRunSummary.objects.filter(survey=survey)
        tree = leaves.aggregate(
            size=Sum("total_size_bytes"),
            directories=Sum("directory_count"),
            files=Sum("file_count"),
        )
        # A full scan of the survey's rows -- 1.9M on bruno, measured under a
        # second, and this runs once per cluster rather than per page.
        whole = DirectorySummary.objects.filter(survey=survey).aggregate(
            size=Sum("total_size_bytes"),
            directories=Count("id"),
            files=Sum("file_count"),
        )

        tree_size = tree["size"] or 0
        tree_dirs = tree["directories"] or 0
        total_size = whole["size"] or 0
        total_dirs = whole["directories"] or 0

        return Response(
            {
                "survey": self._survey_block(),
                "total": _size_block(total_size, total_dirs, whole["files"] or 0),
                "inTree": {
                    **_size_block(tree_size, tree_dirs, tree["files"] or 0),
                    "sessionCount": leaves.values("session_name").distinct().count(),
                    "unregisteredSessionCount": (
                        leaves.filter(msi_session__isnull=True).values("session_name").distinct().count()
                    ),
                    # Session-root leaves are not runs; they carry files sitting
                    # directly under the session directory.
                    "runCount": leaves.exclude(run_name="").count(),
                },
                "outsideTree": _size_block(
                    total_size - tree_size,
                    total_dirs - tree_dirs,
                    (whole["files"] or 0) - (tree["files"] or 0),
                ),
                "bySoftware": [
                    {
                        "software": row["software"],
                        **_size_block(row["size"], row["directories"], row["files"]),
                        "sessionCount": row["sessions"],
                    }
                    for row in leaves.values("software")
                    .annotate(
                        size=Sum("total_size_bytes"),
                        directories=Sum("directory_count"),
                        files=Sum("file_count"),
                        sessions=Count("session_name", distinct=True),
                    )
                    .order_by("-size")
                ],
            },
        )

    @extend_schema(
        tags=["Storage Explorer"],
        summary="Filter options for the storage explorer sidebar",
        description=("Sidebar options for the list endpoint's filter categories. Counts are number of sessions"),
        parameters=[
            OpenApiParameter(
                name="cluster",
                description="Cluster id. Options are drawn from that cluster's newest completed survey.",
                required=False,
                type=str,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Keyed by filter category; the same categories the list endpoint accepts.",
                        "additionalProperties": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "example": "aretomo3"},
                                    "count": {
                                        "type": "integer",
                                        "example": 159,
                                        "description": "Matching sessions, not directories.",
                                    },
                                    "selected": {
                                        "type": "boolean",
                                        "description": "Whether the request's `q` param already selects this option.",
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    )
    @action(detail=False, methods=["get"])
    def filterlist(self, request):
        leaves = self._leaf_queryset()
        facets = {
            "project": value_counts(leaves, "msi_session__project__name", count="session_name"),
            "user": value_counts(leaves, "msi_session__user__username", count="session_name"),
            "owner": value_counts(leaves, "owner_username", count="session_name"),
            "processingSoftware": value_counts(leaves, "software", count="session_name"),
        }
        return Response({"filters": build_filters(request, facets)})


@extend_schema_view(
    list=extend_schema(
        tags=["Storage Explorer"],
        summary="List recorded preservation decisions",
        description=("Paginated and filterable through the shared `q` protocol."),
        parameters=[
            OpenApiParameter(name="cluster", description="Filter to one cluster.", required=False, type=str),
        ],
    ),
    destroy=extend_schema(
        tags=["Storage Explorer"],
        summary="Remove one decision",
        description=(
            "Deletes the record of a judgement. Nothing on the filesystem is touched.\n\n"
            "Posting `status: unset` for the same paths does the same thing and is what the UI uses, "
            "since it already knows the paths and would otherwise have to look up row ids."
        ),
    ),
)
class StorageDecisionViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    Records human judgements about which directories look reclaimable.

    **Nothing here deletes, moves or modifies a file.** ``status = "delete"``
    writes a row to StorageDecision and nothing else: no filesystem write, no
    ``rm``, no SLURM job, no cluster call. Acting on these decisions is
    deliberately a separate feature that has not been built. If a change to this
    module starts touching ``common/clusterio.py``, submitting a job, or writing
    to a path, it is out of scope and needs its own design review.
    """

    serializer_class = StorageDecisionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = EntityTablePagination
    filter_backends = [TableQueryFilter]

    table_filters = {
        "cluster": "cluster__in",
        "status": "status__in",
        # Derived from the path; see session_filter for why there is no column.
        "session": session_filter,
    }
    table_search_fields = ["path_prefix", "notes"]
    table_sort_fields = {
        "decidedAt": "decided_at",
        "path": "path_prefix",
        "status": "status",
        "decidedBy": "decided_by__username",
    }
    # Newest first: the useful question is usually "what was decided recently".
    table_default_sort = ("decidedAt", False)

    def get_queryset(self):
        queryset = StorageDecision.objects.select_related("decided_by")
        cluster = self.request.query_params.get("cluster")
        return queryset.filter(cluster=cluster) if cluster else queryset

    @extend_schema(
        tags=["Storage Explorer"],
        summary="Record a decision across one or more directories",
        description=("Writes one judgement over every path in `path_prefixes`, in a single transaction."),
        request=StorageDecisionWriteSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "cleared": {
                        "type": "integer",
                        "description": "Rows removed, non-zero only for `status: unset`.",
                    },
                    "result": {"type": "array", "items": {"type": "object"}},
                },
            },
        },
    )
    def create(self, request, *args, **kwargs):
        form = StorageDecisionWriteSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        decision = form.validated_data

        cluster = decision["cluster"]
        prefixes = decision["path_prefixes"]

        # Atomic so a multi-prefix session decision cannot land half-applied.
        with transaction.atomic():
            if decision["status"] == UNSET:
                cleared, _ = StorageDecision.objects.filter(cluster=cluster, path_prefix__in=prefixes).delete()
                return Response({"cleared": cleared, "result": []})

            rows = [
                StorageDecision.objects.update_or_create(
                    cluster=cluster,
                    path_prefix=prefix,
                    defaults={
                        "status": decision["status"],
                        "notes": decision["notes"],
                        "decided_by": request.user,
                    },
                )[0]
                for prefix in prefixes
            ]

        return Response({"cleared": 0, "result": StorageDecisionSerializer(rows, many=True).data})
