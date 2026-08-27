"""Unit tests for SubmissionDatasetSerializer.get_type "."""

from types import SimpleNamespace

from depositions.serializers import SubmissionDatasetSerializer


def _annotation(is_selected):
    return SimpleNamespace(is_selected=is_selected)


def _session(*, annotations=(), tomogram=False, tiltseries=False):
    s = SimpleNamespace(
        annotations=SimpleNamespace(all=lambda: list(annotations)),
        tomogram_metadata=SimpleNamespace(exists=lambda: tomogram),
    )
    if tiltseries:
        s.tiltseries_metadata = object() 
    return s


def _dataset(sessions):
    return SimpleNamespace(sessions=SimpleNamespace(all=lambda: list(sessions)))


def _type(dataset):
    return SubmissionDatasetSerializer().get_type(dataset)


class TestDatasetTypeDerivation:
    def test_tomos_only_when_no_selected_annotations(self):
        assert _type(_dataset([_session(tomogram=True)])) == "Tomos only"

    def test_dataset_when_annotations_plus_tomogram_metadata(self):
        ds = _dataset([_session(annotations=[_annotation(True)], tomogram=True)])
        assert _type(ds) == "Dataset"

    def test_annotations_only_when_annotations_and_no_tomogram_metadata(self):
        ds = _dataset([_session(annotations=[_annotation(True)])])
        assert _type(ds) == "Annotations only"

    def test_tiltseries_metadata_also_counts_as_tomograms(self):
        ds = _dataset([_session(annotations=[_annotation(True)], tiltseries=True)])
        assert _type(ds) == "Dataset"

    def test_unselected_annotations_do_not_count(self):
        ds = _dataset([_session(annotations=[_annotation(False)], tomogram=True)])
        assert _type(ds) == "Tomos only"

    def test_empty_dataset_is_tomos_only(self):
        assert _type(_dataset([])) == "Tomos only"
