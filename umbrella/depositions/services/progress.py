"""Collect numeric progress snapshots without affecting submission state."""

import json
import logging
import math
from datetime import datetime, timezone

from django.db.models import Q
from workflow.processors import get_processor

from common import clusterio
from depositions.models import DatasetJob

logger = logging.getLogger(__name__)
LABELS = {"Alignment", "CTF", "Tilt series", "Tomograms", "Masks", "Metadata", "Frames"}


def _count(value):
    if type(value) is not int or not 0 <= value < 2**63:
        raise ValueError("Invalid progress count")
    return value


def _timestamp(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid progress timestamp")
    return value


def collect(job, phase, cluster_id, slurm_job_id, auth):
    """Best-effort capture; reject stale attempts and decreasing counts."""
    try:
        if not auth:
            return None
        directory = get_processor(f"deposition-{phase}").get_script_directory(cluster=cluster_id)
        path = f"{directory.rstrip('/')}/deposition-{phase}-{slurm_job_id}.progress.json"
        raw = json.loads(clusterio.read_remote_file_tail(cluster_id, path, max_bytes=16384, auth=auth))
        sample = {
            "done": _count(raw["done"]),
            "total": _count(raw["total"]),
            "started_at": _timestamp(raw["started_at"]),
            "updated_at": _timestamp(raw["updated_at"]),
            "initial_done": _count(raw.get("initial_done", 0)),
        }
        if sample["done"] > sample["total"] or sample["updated_at"] < sample["started_at"]:
            raise ValueError("Inconsistent progress snapshot")
        if phase == "push" and "estimated" in raw:
            sample["estimated"] = raw["estimated"] is True
        if phase == "prep":
            if raw.get("complete") is True:
                sample["complete"] = True
            sample["items"] = [
                {"label": item["label"], "done": _count(item["done"]), "total": _count(item["total"])}
                for item in raw.get("items", [])
                if item.get("label") in LABELS
            ]
        elif "objects" in raw:
            objects = raw["objects"]
            sample["objects"] = {
                "done": _count(objects["done"]),
                "total": _count(objects["total"]) if objects.get("total") is not None else None,
                "estimated": objects.get("estimated") is True,
            }
            if sample["objects"]["total"] is not None and sample["objects"]["done"] > sample["objects"]["total"]:
                raise ValueError("Inconsistent uploaded object counts")
        field = "sync_progress" if phase == "prep" else "push_progress"
        attempt = f"{phase}_slurm_job_id"
        qs = DatasetJob.objects.filter(
            pk=job.pk, state__in=(f"{phase}_submitted", f"{phase}_running"), **{attempt: slurm_job_id}
        ).filter(
            Q(**{f"{field}__isnull": True})
            | (Q(**{f"{field}__done__lte": sample["done"]}) & Q(**{f"{field}__updated_at__lte": sample["updated_at"]}))
        )
        if not qs.update(**{field: sample}):
            return None
        if phase == "prep" and raw.get("complete") is True:
            summary = raw["summary"]
            return {"objects": _count(summary["objects"]), "bytes": _count(summary["bytes"])}
    except Exception:
        logger.warning("Progress unavailable for %s job %s", phase, slurm_job_id, exc_info=True)
    return None


def format_duration(seconds):
    seconds = max(0, math.ceil(seconds))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m {seconds}s" if minutes else f"{seconds}s"


def format_bytes(value):
    value = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if value < 1024 or unit == "PiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024


def serialize_progress(raw):
    if not raw:
        return None
    done, total = raw["done"], raw["total"]
    result = {"done": done, "total": total, "eta": None}
    if raw.get("complete") is True:
        result["completed_at"] = datetime.fromtimestamp(raw["updated_at"], timezone.utc).isoformat()
    if "estimated" in raw:
        result["estimated"] = raw["estimated"]
    if "items" in raw:
        result["items"] = raw["items"]
    advanced = done - raw.get("initial_done", 0)
    elapsed = raw["updated_at"] - raw["started_at"]
    if "objects" in raw:
        result["objects"] = raw["objects"]
        result["elapsed"] = format_duration(elapsed)
    if not raw.get("estimated", False) and 0 < done < total and advanced > 0 and elapsed > 0:
        result["eta"] = format_duration((total - done) * elapsed / advanced)
    return result


def serialize_summary(job):
    if not job.sync_summary:
        return None
    result = {"objects": job.sync_summary["objects"], "size": format_bytes(job.sync_summary["bytes"])}
    raw = job.sync_progress or {}
    end = (
        datetime.fromtimestamp(raw["updated_at"], timezone.utc)
        if raw.get("complete") is True
        else job.prep_completed_at or job.completed_at
    )
    if end and job.started_at:
        result["duration"] = format_duration((end - job.started_at).total_seconds())
    return result
