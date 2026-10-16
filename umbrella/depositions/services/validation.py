"""Validate the attempt-tagged pre-flight result published at the end of the prep log."""

import json

from depositions.services.exceptions import SubmissionValidationError

MARKER = "DEPOSITION_VALIDATION="


def result_for_attempt(text, attempt, dataset_id):
    fallback = {"status": "unavailable", "attempt": attempt, "warnings": [], "blocking_issues": []}
    try:
        line = next(line for line in reversed((text or "").splitlines()) if line.startswith(MARKER))
        result = json.loads(line[len(MARKER) :])
        if result["attempt"] != attempt or result["dataset_id"] != dataset_id:
            return fallback
        if result["status"] not in ("passed", "failed", "unavailable"):
            return fallback
        for key in ("warnings", "blocking_issues"):
            if not isinstance(result[key], list) or len(result[key]) > 20:
                return fallback
            if any(not isinstance(item, dict) or not isinstance(item.get("message"), str) for item in result[key]):
                return fallback
        if result["status"] == "passed" and result["blocking_issues"]:
            return fallback
        return result
    except (StopIteration, ValueError, KeyError, TypeError):
        return fallback


def require_validation(job):
    if job.state != "prep_completed":
        raise SubmissionValidationError(f"Push can only start from prep_completed, not {job.state!r}.")
    result = job.validation or {}
    if (
        result.get("status") != "passed"
        or not job.prep_slurm_job_id
        or result.get("attempt") != job.prep_slurm_job_id
        or result.get("blocking_issues") != []
    ):
        raise SubmissionValidationError(
            "Upload requires passed pre-flight validation for the current preparation. "
            "Correct any blocking issues and retry preparation and validation."
        )
