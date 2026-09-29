"""State-machine contract for DatasetJob (#860)."""

import pytest

from depositions.models import DatasetJob

ALL_STATES = [s for s, _ in DatasetJob.STATE_CHOICES]
ACTIVE_STATES = [s for s in ALL_STATES if s not in {"pending", "completed", "failed"}]


def test_every_state_maps_to_a_dataset_status():
    # The syncer reads dataset_status for any state, so all must be mapped.
    assert set(DatasetJob.DATASET_STATUS) == set(ALL_STATES)
    assert set(DatasetJob.DATASET_STATUS.values()) <= {"syncing", "pushed", "failed"}
    # Per the signed-off design: draft = no job; any live job state is syncing+.
    assert DatasetJob.DATASET_STATUS["pending"] == "syncing"


def test_only_pending_and_failed_are_editable():
    assert set(ALL_STATES) - {"pending", "failed"} == DatasetJob.LOCKED_STATES
    assert not DatasetJob(state="pending").is_locked
    assert not DatasetJob(state="failed").is_locked
    assert DatasetJob(state="prep_completed").is_locked
    assert DatasetJob(state="push_running").is_locked


def test_prep_completed_advances_only_to_push_submitted():
    # prep_completed's sole forward move is push_submitted, never
    # push_running/completed; the user's Submit click triggers it (#860 endpoint).
    job = DatasetJob(state="prep_completed")
    assert job.can_transition_to("push_submitted")
    assert not job.can_transition_to("push_running")
    assert not job.can_transition_to("completed")


def test_short_job_may_skip_its_running_state():
    # A poll can miss the running state, so *_submitted -> completion is allowed.
    assert DatasetJob(state="prep_submitted").can_transition_to("prep_completed")
    assert DatasetJob(state="push_submitted").can_transition_to("completed")


def test_prep_completed_can_reset_to_pending():
    # prep_completed can return to pending (invalidating prep).
    assert DatasetJob(state="prep_completed").can_transition_to("pending")


def test_failed_can_retry_prep():
    assert DatasetJob(state="failed").can_transition_to("prep_submitted")


def test_completed_is_terminal():
    assert DatasetJob.TRANSITIONS["completed"] == set()


@pytest.mark.parametrize("state", ACTIVE_STATES)
def test_any_active_state_can_fail(state):
    assert DatasetJob(state=state).can_transition_to("failed")


def test_transition_to_sets_state_on_valid_move():
    job = DatasetJob(state="pending")
    job.transition_to("prep_submitted")
    assert job.state == "prep_submitted"


def test_transition_to_rejects_invalid_move():
    job = DatasetJob(state="pending")
    with pytest.raises(ValueError):
        job.transition_to("completed")
    assert job.state == "pending"
