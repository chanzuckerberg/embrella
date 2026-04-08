"""
Filesystem survey and directory browsing view functions.

This module contains views for managing filesystem surveys and browsing
directory-level aggregates from survey results.
"""

import json
import logging
import os
import tempfile
from datetime import datetime

import pytz
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view

from common import clusterio
from processes.models import DirectorySummary, FilesystemSurvey

logger = logging.getLogger(__name__)


@extend_schema(
    methods=["GET"],
    description="Returns list of filesystem surveys with their status and statistics.",
    parameters=[
        OpenApiParameter(name="cluster", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="status", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="page", required=False, type=int),
        OpenApiParameter(name="pageSize", required=False, type=int),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_surveys(request):
    """
    Get paginated list of filesystem surveys.
    """
    try:
        # Pagination
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("pageSize", 10))

        # Filters
        cluster = request.GET.get("cluster")
        status = request.GET.get("status")

        queryset = FilesystemSurvey.objects.select_related("submitted_by").order_by("-created_at")

        if cluster:
            queryset = queryset.filter(cluster=cluster)
        if status:
            queryset = queryset.filter(status=status)

        # Paginate
        paginator = Paginator(queryset, page_size, orphans=3)
        try:
            page_obj = paginator.page(page)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)

        # Serialize results
        surveys = []
        for survey in page_obj:
            surveys.append(
                {
                    "id": survey.id,
                    "cluster": survey.cluster,
                    "base_path": survey.base_path,
                    "status": survey.status,
                    "job_id": survey.job_id,
                    "total_files": survey.total_files,
                    "total_directories": survey.total_directories,
                    "total_size_bytes": survey.total_size_bytes,
                    "total_size_display": survey.get_size_display(),
                    "submitted_by": survey.submitted_by.username if survey.submitted_by else None,
                    "submitted_at": survey.submitted_at.isoformat() if survey.submitted_at else None,
                    "completed_at": survey.completed_at.isoformat() if survey.completed_at else None,
                    "error_message": survey.error_message,
                    "created_at": survey.created_at.isoformat(),
                }
            )

        return JsonResponse(
            {
                "surveys": surveys,
                "totalCount": paginator.count,
                "totalPages": paginator.num_pages,
                "currentPage": page_obj.number,
            }
        )

    except Exception as e:
        logger.exception(f"Error fetching surveys: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    methods=["GET"],
    description="Returns paginated directory summaries with filtering support.",
    parameters=[
        OpenApiParameter(name="survey_id", required=False, type=int),
        OpenApiParameter(name="cluster", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="origin", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="preserve_status", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="owner_username", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name="path_prefix", required=False, type=OpenApiTypes.STR),
        OpenApiParameter(
            name="path_contains",
            required=False,
            type=OpenApiTypes.STR,
            description="Search for paths containing this string (case-insensitive)",
        ),
        OpenApiParameter(name="min_depth", required=False, type=int),
        OpenApiParameter(name="max_depth", required=False, type=int),
        OpenApiParameter(
            name="sort_field",
            required=False,
            type=OpenApiTypes.STR,
            description="Sort by: path, total_size_bytes, file_count, preserve_status, newest_file_mtime",
        ),
        OpenApiParameter(
            name="sort_order",
            required=False,
            type=OpenApiTypes.STR,
            description="Sort order: asc or desc (default: asc)",
        ),
        OpenApiParameter(name="page", required=False, type=int),
        OpenApiParameter(name="pageSize", required=False, type=int),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_directories(request):
    """
    Get paginated list of directory summaries with filtering.
    """
    try:
        # Pagination
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("pageSize", 50))

        # Sorting
        sort_field = request.GET.get("sort_field", "path")
        sort_order = request.GET.get("sort_order", "asc")

        # Validate sort field
        valid_sort_fields = ["path", "total_size_bytes", "file_count", "preserve_status", "newest_file_mtime"]
        if sort_field not in valid_sort_fields:
            sort_field = "path"

        # Build order_by clause
        order_by = f"-{sort_field}" if sort_order == "desc" else sort_field

        # Filters
        survey_id = request.GET.get("survey_id")
        cluster = request.GET.get("cluster")
        origin = request.GET.get("origin")
        preserve_status = request.GET.get("preserve_status")
        owner_username = request.GET.get("owner_username")
        path_prefix = request.GET.get("path_prefix")
        path_contains = request.GET.get("path_contains")
        min_depth = request.GET.get("min_depth")
        max_depth = request.GET.get("max_depth")

        queryset = DirectorySummary.objects.select_related("survey", "status_updated_by", "content_type").order_by(
            order_by
        )

        if survey_id:
            queryset = queryset.filter(survey_id=survey_id)
        if cluster:
            queryset = queryset.filter(cluster=cluster)
        if origin:
            queryset = queryset.filter(origin=origin)
        if preserve_status:
            queryset = queryset.filter(preserve_status=preserve_status)
        if owner_username:
            queryset = queryset.filter(owner_username=owner_username)
        if path_prefix:
            queryset = queryset.filter(path__startswith=path_prefix)
        if path_contains:
            queryset = queryset.filter(path__icontains=path_contains)
        if min_depth:
            queryset = queryset.filter(depth__gte=int(min_depth))
        if max_depth:
            queryset = queryset.filter(depth__lte=int(max_depth))

        # Paginate
        paginator = Paginator(queryset, page_size, orphans=3)
        try:
            page_obj = paginator.page(page)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.page(1)

        # Serialize results
        directories = []
        for d in page_obj:
            # Build linked_entity info if content_type is set
            linked_entity = None
            if d.content_type and d.object_id:
                linked_entity = {
                    "type": d.content_type.model,
                    "id": d.object_id,
                    "app_label": d.content_type.app_label,
                }

            directories.append(
                {
                    "id": d.id,
                    "survey_id": d.survey_id,
                    "cluster": d.cluster,
                    "path": d.path,
                    "file_count": d.file_count,
                    "total_size_bytes": d.total_size_bytes,
                    "total_size_display": d.get_size_display(),
                    "owner_username": d.owner_username,
                    "owner_uid": d.owner_uid,
                    "origin": d.origin,
                    "preserve_status": d.preserve_status,
                    "status_updated_at": d.status_updated_at.isoformat() if d.status_updated_at else None,
                    "status_updated_by": d.status_updated_by.username if d.status_updated_by else None,
                    "depth": d.depth,
                    "newest_file_mtime": d.newest_file_mtime.isoformat() if d.newest_file_mtime else None,
                    "oldest_file_mtime": d.oldest_file_mtime.isoformat() if d.oldest_file_mtime else None,
                    "linked_entity": linked_entity,
                }
            )

        return JsonResponse(
            {
                "directories": directories,
                "totalCount": paginator.count,
                "totalPages": paginator.num_pages,
                "currentPage": page_obj.number,
            }
        )

    except Exception as e:
        logger.exception(f"Error fetching directories: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    methods=["GET"],
    description="Returns directory storage statistics aggregated by various dimensions.",
    parameters=[
        OpenApiParameter(name="survey_id", required=False, type=int),
        OpenApiParameter(name="cluster", required=False, type=OpenApiTypes.STR),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_directory_stats(request):
    """
    Get aggregated storage statistics from directory summaries.
    """
    try:
        survey_id = request.GET.get("survey_id")
        cluster = request.GET.get("cluster")

        queryset = DirectorySummary.objects.all()

        if survey_id:
            queryset = queryset.filter(survey_id=survey_id)
        if cluster:
            queryset = queryset.filter(cluster=cluster)

        # Get statistics by origin
        by_origin = (
            queryset.values("origin")
            .annotate(
                total_size=Sum("total_size_bytes"),
                total_files=Sum("file_count"),
                directory_count=Count("id"),
            )
            .order_by("origin")
        )

        # Get statistics by preserve_status
        by_status = (
            queryset.values("preserve_status")
            .annotate(
                total_size=Sum("total_size_bytes"),
                total_files=Sum("file_count"),
                directory_count=Count("id"),
            )
            .order_by("preserve_status")
        )

        # Get statistics by owner
        by_owner = (
            queryset.values("owner_username")
            .annotate(
                total_size=Sum("total_size_bytes"),
                total_files=Sum("file_count"),
                directory_count=Count("id"),
            )
            .order_by("-total_size")[:20]
        )  # Top 20 owners

        # Total statistics
        totals = queryset.aggregate(
            total_size=Sum("total_size_bytes"),
            total_files=Sum("file_count"),
            directory_count=Count("id"),
        )

        def format_size(size_bytes):
            if size_bytes is None:
                return "0 B"
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} PB"

        return JsonResponse(
            {
                "totals": {
                    "total_size_bytes": totals["total_size"] or 0,
                    "total_size_display": format_size(totals["total_size"]),
                    "total_files": totals["total_files"] or 0,
                    "directory_count": totals["directory_count"] or 0,
                },
                "by_origin": [
                    {
                        "origin": item["origin"],
                        "total_size_bytes": item["total_size"] or 0,
                        "total_size_display": format_size(item["total_size"]),
                        "total_files": item["total_files"] or 0,
                        "directory_count": item["directory_count"],
                    }
                    for item in by_origin
                ],
                "by_status": [
                    {
                        "preserve_status": item["preserve_status"],
                        "total_size_bytes": item["total_size"] or 0,
                        "total_size_display": format_size(item["total_size"]),
                        "total_files": item["total_files"] or 0,
                        "directory_count": item["directory_count"],
                    }
                    for item in by_status
                ],
                "by_owner": [
                    {
                        "owner_username": item["owner_username"],
                        "total_size_bytes": item["total_size"] or 0,
                        "total_size_display": format_size(item["total_size"]),
                        "total_files": item["total_files"] or 0,
                        "directory_count": item["directory_count"],
                    }
                    for item in by_owner
                ],
            }
        )

    except Exception as e:
        logger.exception(f"Error fetching directory stats: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    methods=["POST"],
    description="Bulk update preserve_status for multiple directories.",
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
@api_view(["POST"])
@require_http_methods(["POST"])
def bulk_update_directory_status(request):
    """
    Bulk update preserve_status for multiple directories.

    Expected JSON body:
    {
        "directory_ids": [1, 2, 3],
        "preserve_status": "preserve" | "delete" | "review" | "unset"
    }
    """
    try:
        data = json.loads(request.body)
        directory_ids = data.get("directory_ids", [])
        preserve_status = data.get("preserve_status")

        if not directory_ids:
            return JsonResponse({"error": "No directory_ids provided"}, status=400)

        valid_statuses = ["unset", "preserve", "delete", "review"]
        if preserve_status not in valid_statuses:
            return JsonResponse(
                {
                    "error": f"Invalid preserve_status. Must be one of: {valid_statuses}",
                },
                status=400,
            )

        # Update directories
        updated = DirectorySummary.objects.filter(id__in=directory_ids).update(
            preserve_status=preserve_status,
            status_updated_at=timezone.now(),
            status_updated_by=request.user if request.user.is_authenticated else None,
        )

        return JsonResponse(
            {
                "success": True,
                "updated_count": updated,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception(f"Error updating directory status: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    methods=["GET"],
    description="Returns filter options for directories (unique origins, statuses, owners).",
    parameters=[
        OpenApiParameter(name="survey_id", required=False, type=int),
        OpenApiParameter(name="cluster", required=False, type=OpenApiTypes.STR),
    ],
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_directory_filterlist(request):
    """
    Get available filter values for directories.

    Returns data in the format expected by EntityTableFilters:
    {
        "filters": {
            "category": [{"name": "value", "count": 10, "selected": false}, ...]
        }
    }
    """
    try:
        survey_id = request.GET.get("survey_id")
        cluster = request.GET.get("cluster")

        queryset = DirectorySummary.objects.all()

        if survey_id:
            queryset = queryset.filter(survey_id=survey_id)
        if cluster:
            queryset = queryset.filter(cluster=cluster)

        # Get counts by cluster
        cluster_counts = queryset.values("cluster").annotate(count=Count("id")).order_by("cluster")

        # Get counts by origin
        origin_counts = queryset.values("origin").annotate(count=Count("id")).order_by("origin")

        # Get counts by preserve_status
        status_counts = queryset.values("preserve_status").annotate(count=Count("id")).order_by("preserve_status")

        # Get counts by owner (top 100)
        owner_counts = (
            queryset.exclude(owner_username__isnull=True)
            .values("owner_username")
            .annotate(count=Count("id"))
            .order_by("-count")[:100]
        )

        def format_filter_options(queryset_result, value_field):
            return [{"name": item[value_field], "count": item["count"], "selected": False} for item in queryset_result]

        return JsonResponse(
            {
                "filters": {
                    "cluster": format_filter_options(cluster_counts, "cluster"),
                    "origin": format_filter_options(origin_counts, "origin"),
                    "preserve_status": format_filter_options(status_counts, "preserve_status"),
                    "owner_username": format_filter_options(owner_counts, "owner_username"),
                },
            }
        )

    except Exception as e:
        logger.exception(f"Error fetching directory filterlist: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def format_size(size_bytes):
    """Format bytes as human-readable size."""
    if size_bytes is None:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


@extend_schema(
    methods=["GET"],
    description="Returns files within a directory by querying the survey's Parquet file on-demand.",
    parameters=[
        OpenApiParameter(name="directory_id", required=True, type=int, location="path"),
        OpenApiParameter(
            name="file_type",
            required=False,
            type=OpenApiTypes.STR,
            description="Filter by type: 'file', 'zarr', or 'all' (default: 'all')",
        ),
        OpenApiParameter(name="page", required=False, type=int),
        OpenApiParameter(name="pageSize", required=False, type=int),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_directory_files(request, directory_id):
    """
    Get files within a specific directory by querying the Parquet file.

    This endpoint reads from the survey's Parquet file on-demand to return
    file-level details that aren't stored in the database.
    """
    import duckdb

    try:
        # Get the DirectorySummary
        try:
            directory = DirectorySummary.objects.select_related("survey").get(id=directory_id)
        except DirectorySummary.DoesNotExist:
            return JsonResponse({"error": "Directory not found"}, status=404)

        survey = directory.survey
        if not survey.results_parquet_path:
            return JsonResponse({"error": "Survey has no Parquet file"}, status=400)

        # Parameters
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("pageSize", 100))
        file_type = request.GET.get("file_type", "all")

        # Build type filter
        if file_type == "file":
            type_filter = "type = 'file'"
        elif file_type == "zarr":
            type_filter = "type = 'zarr'"
        else:
            type_filter = "type IN ('file', 'zarr')"

        # Download Parquet file via SFTP
        auth = {
            "username": os.getenv("SLURM_USER"),
            "key_filename": os.getenv("SLURM_KEYFILE"),
        }

        ssh = clusterio.get_cluster_ssh_connection(cluster_id=survey.cluster, auth=auth)

        try:
            sftp = ssh.open_sftp()

            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                tmp_path = tmp.name

            sftp.get(survey.results_parquet_path, tmp_path)
            sftp.close()

            # Query with DuckDB
            con = duckdb.connect()

            # The directory path from DirectorySummary is the parent directory
            # We need to find files whose parent directory matches
            dir_path = directory.path

            # Count total matching files
            count_result = con.execute(f"""
                SELECT COUNT(*) as total
                FROM read_parquet('{tmp_path}')
                WHERE regexp_replace(path, '/[^/]+$', '') = '{dir_path}'
                  AND {type_filter}
            """).fetchone()
            total_count = count_result[0] if count_result else 0

            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            offset = (page - 1) * page_size

            # Get paginated results
            results = con.execute(f"""
                SELECT
                    path,
                    size,
                    mtime,
                    uid,
                    mode,
                    type
                FROM read_parquet('{tmp_path}')
                WHERE regexp_replace(path, '/[^/]+$', '') = '{dir_path}'
                  AND {type_filter}
                ORDER BY path
                LIMIT {page_size}
                OFFSET {offset}
            """).fetchall()

            con.close()

            # Clean up temp file
            os.unlink(tmp_path)

            # Format results
            files = []
            for row in results:
                path, size, mtime, uid, mode, file_type_val = row
                filename = path.split("/")[-1] if path else ""
                files.append(
                    {
                        "path": path,
                        "filename": filename,
                        "size_bytes": size,
                        "size_display": format_size(size),
                        "mtime": datetime.fromtimestamp(mtime, tz=pytz.UTC).isoformat() if mtime else None,
                        "uid": uid,
                        "mode": mode,
                        "type": file_type_val,
                    }
                )

            return JsonResponse(
                {
                    "files": files,
                    "directory": {
                        "id": directory.id,
                        "path": directory.path,
                        "file_count": directory.file_count,
                        "total_size_bytes": directory.total_size_bytes,
                        "total_size_display": directory.get_size_display(),
                    },
                    "survey_id": survey.id,
                    "totalCount": total_count,
                    "totalPages": total_pages,
                    "currentPage": page,
                }
            )

        finally:
            ssh.close()

    except Exception as e:
        logger.exception(f"Error fetching directory files: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    methods=["GET"],
    description="Returns files within a survey by path, querying the Parquet file on-demand.",
    parameters=[
        OpenApiParameter(name="survey_id", required=True, type=int, location="path"),
        OpenApiParameter(
            name="path", required=True, type=OpenApiTypes.STR, description="Directory path to list files from"
        ),
        OpenApiParameter(
            name="file_type",
            required=False,
            type=OpenApiTypes.STR,
            description="Filter by type: 'file', 'zarr', or 'all' (default: 'all')",
        ),
        OpenApiParameter(name="page", required=False, type=int),
        OpenApiParameter(name="pageSize", required=False, type=int),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_survey_files(request, survey_id):
    """
    Get files within a survey at a specific path by querying the Parquet file.

    This is an alternative to get_directory_files that doesn't require a
    DirectorySummary record - useful for browsing arbitrary paths.
    """
    import duckdb

    try:
        # Get the survey
        try:
            survey = FilesystemSurvey.objects.get(id=survey_id)
        except FilesystemSurvey.DoesNotExist:
            return JsonResponse({"error": "Survey not found"}, status=404)

        if not survey.results_parquet_path:
            return JsonResponse({"error": "Survey has no Parquet file"}, status=400)

        # Required parameter
        dir_path = request.GET.get("path")
        if not dir_path:
            return JsonResponse({"error": "path parameter is required"}, status=400)

        # Normalize path (remove trailing slash)
        dir_path = dir_path.rstrip("/")

        # Parameters
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("pageSize", 100))
        file_type = request.GET.get("file_type", "all")

        # Build type filter
        if file_type == "file":
            type_filter = "type = 'file'"
        elif file_type == "zarr":
            type_filter = "type = 'zarr'"
        else:
            type_filter = "type IN ('file', 'zarr')"

        # Download Parquet file via SFTP
        auth = {
            "username": os.getenv("SLURM_USER"),
            "key_filename": os.getenv("SLURM_KEYFILE"),
        }

        ssh = clusterio.get_cluster_ssh_connection(cluster_id=survey.cluster, auth=auth)

        try:
            sftp = ssh.open_sftp()

            # Download to temp file
            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                tmp_path = tmp.name

            sftp.get(survey.results_parquet_path, tmp_path)
            sftp.close()

            # Query with DuckDB
            con = duckdb.connect()

            # Count total matching files
            count_result = con.execute(f"""
                SELECT COUNT(*) as total
                FROM read_parquet('{tmp_path}')
                WHERE regexp_replace(path, '/[^/]+$', '') = '{dir_path}'
                  AND {type_filter}
            """).fetchone()
            total_count = count_result[0] if count_result else 0

            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            offset = (page - 1) * page_size

            # Get paginated results
            results = con.execute(f"""
                SELECT
                    path,
                    size,
                    mtime,
                    uid,
                    mode,
                    type
                FROM read_parquet('{tmp_path}')
                WHERE regexp_replace(path, '/[^/]+$', '') = '{dir_path}'
                  AND {type_filter}
                ORDER BY path
                LIMIT {page_size}
                OFFSET {offset}
            """).fetchall()

            con.close()

            # Clean up temp file
            os.unlink(tmp_path)

            # Format results
            files = []
            for row in results:
                path, size, mtime, uid, mode, file_type_val = row
                filename = path.split("/")[-1] if path else ""
                files.append(
                    {
                        "path": path,
                        "filename": filename,
                        "size_bytes": size,
                        "size_display": format_size(size),
                        "mtime": datetime.fromtimestamp(mtime, tz=pytz.UTC).isoformat() if mtime else None,
                        "uid": uid,
                        "mode": mode,
                        "type": file_type_val,
                    }
                )

            return JsonResponse(
                {
                    "files": files,
                    "path": dir_path,
                    "survey_id": survey.id,
                    "totalCount": total_count,
                    "totalPages": total_pages,
                    "currentPage": page,
                }
            )

        finally:
            ssh.close()

    except Exception as e:
        logger.exception(f"Error fetching survey files: {e}")
        return JsonResponse({"error": str(e)}, status=500)
