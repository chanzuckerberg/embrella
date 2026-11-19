"""Run names are validated so they can't traverse out of the cluster paths they're spliced into."""

import re

import pytest
from rest_framework import serializers

from depositions.serializers import (
    DepositionSessionLinkSerializer,
    DepositionSessionSerializer,
    validate_selected_copick_runs,
)
from depositions.services.exceptions import SubmissionValidationError
from depositions.validators import RUN_NAME_MESSAGE, ensure_safe_run_name

# No slash (can't traverse) and must start alphanumeric (blocks ".", "..", "-rf"). The leading-dash rule
# only matters at the serializer/copick boundary; the denoise/auto-fill paths prepend "run" first.
TRAVERSAL = ["../etc", "run001/../x", "a/b", "..", ".", "-rf", "run 1", "run\n1", "run;rm", "~/x"]
VALID = ["run001", "001", "TS_1", "Position_8_ts_011", "run-2", "run.001", "run002_old"]
# DRF trims these for the CharFields, but fullmatch must still reject them off the serializer path.
TRAILING_NEWLINE = ["run001\n", "run001\t"]


@pytest.mark.django_db
@pytest.mark.parametrize("serializer_class", [DepositionSessionSerializer, DepositionSessionLinkSerializer])
@pytest.mark.parametrize("field", ["aretomo_run_name", "denoise_run_name"])
@pytest.mark.parametrize("bad", TRAVERSAL)
def test_run_name_rejects_traversal(serializer_class, field, bad):
    serializer = serializer_class(data={field: bad}, partial=True)
    assert not serializer.is_valid()
    assert serializer.errors[field][0] == RUN_NAME_MESSAGE


@pytest.mark.django_db
@pytest.mark.parametrize("serializer_class", [DepositionSessionSerializer, DepositionSessionLinkSerializer])
@pytest.mark.parametrize("field", ["aretomo_run_name", "denoise_run_name"])
@pytest.mark.parametrize("good", [*VALID, ""])  # blank is allowed (denoise skipped / run not chosen yet)
def test_run_name_accepts_valid(serializer_class, field, good):
    serializer = serializer_class(data={field: good}, partial=True)
    assert serializer.is_valid(), serializer.errors


@pytest.mark.parametrize("bad", [*TRAVERSAL, *TRAILING_NEWLINE])
def test_selected_copick_runs_rejects_traversal(bad):
    with pytest.raises(serializers.ValidationError, match=re.escape(RUN_NAME_MESSAGE)):
        validate_selected_copick_runs([bad])


def test_selected_copick_runs_accepts_valid():
    assert validate_selected_copick_runs(VALID) == VALID


@pytest.mark.parametrize("bad", [*TRAVERSAL, *TRAILING_NEWLINE])
def test_path_build_guard_rejects_traversal(bad):
    # Defense-in-depth for values that bypassed the serializer (admin edits, legacy rows).
    with pytest.raises(SubmissionValidationError) as exc:
        ensure_safe_run_name(bad)
    assert exc.value.public_message.endswith(RUN_NAME_MESSAGE)


@pytest.mark.parametrize("ok", [*VALID, "", None])
def test_path_build_guard_allows_valid_and_blank(ok):
    ensure_safe_run_name(ok)  # no raise


@pytest.mark.django_db
def test_run_name_over_max_length_is_rejected():
    # The validators override doesn't drop max_length (40), so an over-long name is still caught.
    serializer = DepositionSessionSerializer(data={"aretomo_run_name": "a" * 41}, partial=True)
    assert not serializer.is_valid()
    assert "aretomo_run_name" in serializer.errors
