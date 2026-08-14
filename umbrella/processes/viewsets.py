"""
DRF ViewSets for the processes app.

- **storage-sessions** -- storage rolled up per MSI session, backing the Storage
  Explorer. Reads the materialized StorageRunSummary tree
"""

from collections import defaultdict

from django.db.models import Count, Max, Min, Q, Sum
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from stores.models import Cluster
from umbrella.table_api import EntityTablePagination, TableQueryFilter, build_filters, value_counts

from processes.models import FilesystemSurvey, StorageRunSummary, current_survey
from processes.serializers import StorageSessionSerializer
from processes.services.decisions import decisions_for, effective_status, rollup_status
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
