"""FilePattern: the filename half of a path, and the regex rules enforced on save."""

import pytest
from django.core.exceptions import ValidationError

from stores.models import DataKind, FilePattern, validate_file_regex

pytestmark = pytest.mark.django_db

FRAMES = r"^(?P<run>[A-Za-z0-9]+)_(?P<sequence>\d+)_(?P<tilt>-?[\d.]+)_.*\.eer$"


def make_pattern(regex=FRAMES, samples=()):
    kind, _ = DataKind.objects.get_or_create(data_type="frames")
    return FilePattern(data_kind=kind, label="test", regex=regex, sample_filenames=list(samples))


class TestMatching:
    def test_captures_named_groups(self):
        assert make_pattern().match("Position1_001_-30.0_Fractions.eer") == {
            "run": "Position1",
            "sequence": "001",
            "tilt": "-30.0",
        }

    def test_foreign_basename_is_none(self):
        """None and {} mean different things: 'not ours' vs 'ours, captured nothing'."""
        assert make_pattern().match("Atlas_20241110.mrc") is None

    def test_matches_basename_only(self):
        """The directory half belongs to PathType. A full path must not match."""
        assert make_pattern().match("/hpc/x/24nov10/Position1_001_-30.0_f.eer") is None


class TestRegexRules:
    def test_broken_regex_rejected(self):
        with pytest.raises(ValidationError, match="Not a valid regular expression"):
            validate_file_regex(r"^(?P<run>[unclosed$")

    def test_unanchored_rejected(self):
        """Unanchored, a pattern silently matches anything merely containing it."""
        with pytest.raises(ValidationError, match="Anchor with"):
            validate_file_regex(r"(?P<run>\w+)\.eer")

    def test_positional_groups_rejected(self):
        with pytest.raises(ValidationError, match="Use named groups"):
            validate_file_regex(r"^(\w+)_(?P<tilt>[\d.]+)\.eer$")

    def test_non_capturing_groups_ok(self):
        """(?:...) has no name because it captures nothing -- not the mistake being caught."""
        assert validate_file_regex(r"^(?P<run>\w+)(?:_alt)?\.eer$")


class TestReDoSGuard:
    """These regexes run against every basename in a directory inside a django-q worker,
    where catastrophic backtracking is a hung job with no obvious cause."""

    @pytest.mark.parametrize(
        "regex",
        [
            r"^(?P<run>\w+)*\.eer$",
            r"^(?:\w+\s*)+\.eer$",
            r"^(?P<x>.+)*\.eer$",
            r"^(?:a+){2,}\.eer$",
        ],
    )
    def test_rejects_nested_unbounded_quantifiers(self, regex):
        with pytest.raises(ValidationError, match="backtrack catastrophically"):
            validate_file_regex(regex)

    def test_separator_anchored_repeat_passes(self):
        """The 2e rec pattern: each repetition starts with a literal '_', so the split is
        unambiguous and backtracking stays linear."""
        assert validate_file_regex(r"^(?P<position>Position_\d+(?:_\d+)*)_Vol\.zarr$")

    def test_bounded_quantifier_passes(self):
        assert validate_file_regex(r"^(?P<tilt>-?\d+(?:\.\d+)?)\.eer$")

    def test_freestyle_stem_passes(self):
        """The serialEM rec pattern: an unquantified group holding one unbounded repeat is linear."""
        assert validate_file_regex(r"^(?P<position>.+)\.mrc_Vol\.zarr$")


class TestCompiled:
    def test_bad_regex_raises_at_first_read(self):
        """clean() only runs in admin; a row from .objects.create(), a data migration, or a
        restored dump reaches the read site unchecked. Better an actionable error there
        than a regex that silently matches nothing."""
        pattern = make_pattern(regex=r"(?P<run>\w+)\.eer")  # unanchored, as clean() would have caught
        with pytest.raises(ValidationError, match="Anchor with"):
            pattern.match("Position1.eer")


class TestSampleFilenames:
    def test_unmatched_sample_rejected(self):
        """Names the failing file: an error that doesn't say which is useless with ten samples."""
        with pytest.raises(ValidationError, match="does not match 'not-a-frame.txt'"):
            make_pattern(samples=["Position1_001_-30.0_f.eer", "not-a-frame.txt"]).clean()

    def test_matching_samples_pass(self):
        make_pattern(samples=["Position1_001_-30.0_f.eer", "P2_002_0.0_x.eer"]).clean()
