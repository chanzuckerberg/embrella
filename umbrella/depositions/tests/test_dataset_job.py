"""DatasetJob status mapping and cluster-freeze contract."""

from depositions.models import DatasetJob

ALL_STATES = [s for s, _ in DatasetJob.STATE_CHOICES]


def test_every_state_maps_to_a_dataset_status():
    # The syncer reads dataset_status for any state, so all must be mapped.
    assert set(DatasetJob.DATASET_STATUS) == set(ALL_STATES)
    assert set(DatasetJob.DATASET_STATUS.values()) <= {"draft", "syncing", "pushed", "failed"}
    # Reset jobs return to draft so metadata can be corrected before a new prep.
    assert DatasetJob.DATASET_STATUS["pending"] == "draft"


def test_only_pending_and_failed_allow_cluster_selection():
    assert set(ALL_STATES) - {"pending", "failed"} == DatasetJob.CLUSTER_FROZEN_STATES
    assert not DatasetJob(state="pending").cluster_is_frozen
    assert not DatasetJob(state="failed").cluster_is_frozen
    assert DatasetJob(state="prep_completed").cluster_is_frozen
    assert DatasetJob(state="push_running").cluster_is_frozen
