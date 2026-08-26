"""Tests for the path-template placeholder vocabulary.

Templates are mirrored as literals rather than imported, because the seeds build them
inside `run()` bodies. Same approach as tem/tests/test_session_paths.py -- when a
template changes in a seed, it has to change here too, which is the point.

No database: the vocabulary is pure Python and should stay that way.
"""

import pytest

from stores.placeholders import (
    FILE_SCOPED,
    PLACEHOLDERS,
    SESSION_SCOPED,
    Placeholder,
    file_scoped_placeholders,
    known_placeholders,
    misplaced_placeholders,
    placeholders_in,
    session_scoped_placeholders,
    suggest_placeholder,
    unknown_placeholders,
)

# Directory halves only, since stores/0020 split the filenames off onto FilePattern rows.
# scripts/001_init.py:126-169 and scripts/003_init_multigrid.py:30-46
ACQUISITION_TEMPLATES = [
    "/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/",
    "/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{msi_session}/Batch/",
    "/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session_group}/{atlas_session}/Atlas/",
]

# scripts/004_init_processes.py:107-156, 005_init_pytom_pick.py:100-113,
# and 006_init_copick_octopi.py:92-99
PROCESSING_TEMPLATES = [
    "/hpc/projects/group.czii/{scope}.processing/{proc_software}/{msi_session}/{proc_run}/",
    "/hpc/projects/group.czii/{scope}.processing/{proc_software}/{msi_session}/{proc_run}/{run}_TLT.txt",
    "/hpc/projects/group.czii/{scope}.processing/{proc_software}/{msi_session}/{proc_run}/{run}.mrc",
    "/hpc/projects/group.czii/{scope}.processing/{proc_software}/{msi_session}/{proc_run}/{run}_Imod/",
    "/hpc/projects/group.czii/{scope}.processing/{proc_software}/{msi_session}/{proc_run}/{pipe}/{run}_Vol.mrc",
    "/hpc/projects/group.czii/{scope}.processing/{proc_software}/{msi_session}/{pipe}/{proc_run}/{run}/output.txt",
    "/{msi_session}/{run}/rec/{proc_software}/{proc_run}/{pipe}/",
]

# stores/migrations/0011_review_pathtypes.py, 0012_copick_url_pathtype.py,
# 0013_proc_url_pathtype.py, and the flattened variants in scripts/populate_demo.py:110-113
REVIEW_TEMPLATES = [
    "/hpc/projects/group.czii/{scope}.processing/{workflow}/{msi_session}/{run}/",
    "{http_base}{scope}.processing/{workflow}/{msi_session}/{run}/{vol_suffix}/{position}_Vol.zarr",
    "{http_base}{scope}.processing/aretomo3/{msi_session}/{run}/{thumb_kind}/",
    "{http_base}{scope}.processing/copick/{msi_session}/{copick_run}/",
    "/{workflow}/{msi_session}/{run}/proc_dir",
    "/aretomo3/{msi_session}/{run}/{thumb_kind}/",
    "/copick/{msi_session}/{copick_run}/",
    "{http_base}{workflow}/{msi_session}/{run}/",
    "{http_base}aretomo3/{msi_session}/{run}/{thumb_kind}/",
    "{http_base}{workflow}/{msi_session}/{run}/{vol_suffix}/{position}_Vol.zarr",
]

SEEDED_TEMPLATES = ACQUISITION_TEMPLATES + PROCESSING_TEMPLATES + REVIEW_TEMPLATES


class TestSeededTemplates:
    @pytest.mark.parametrize("template", SEEDED_TEMPLATES)
    def test_every_shipped_template_uses_only_known_tokens(self, template):
        assert unknown_placeholders(template) == frozenset()


class TestVocabulary:
    def test_partitions_into_session_and_file_scoped(self):
        session, files = session_scoped_placeholders(), file_scoped_placeholders()
        assert session | files == known_placeholders()
        assert session & files == frozenset()

    def test_each_token_is_declared_once(self):
        """The point of the flat table: no name appears twice, so there is no second
        declaration to fall out of sync with the first."""
        names = [p.name for p in PLACEHOLDERS]
        assert len(names) == len(set(names))

    def test_placeholder_rejects_a_bad_scope(self):
        with pytest.raises(ValueError, match="scope must be"):
            Placeholder("x", "directory", "nowhere")


class TestOverloadedTokens:
    """Three tokens are read differently by acquisition, processing and review
    templates. Each is declared under its true meaning"""

    def test_workflow_is_the_imaging_workflow(self):
        """Review templates overload it as the processing software -- that is
        {proc_software}, and both are legal tokens, so this is documentation rather
        than something the validator can catch."""
        assert "workflow" in session_scoped_placeholders()
        assert "proc_software" in session_scoped_placeholders()

    def test_run_is_file_scoped_and_proc_run_is_not(self):
        """004's templates put {proc_run} and {run} in the same path -- not synonyms.
        {run} is a tilt-series id in a filename; the processing run is {proc_run}."""
        assert "run" in file_scoped_placeholders()
        assert "proc_run" in session_scoped_placeholders()

    def test_position_is_file_scoped(self):
        """Review pre-substitutes it from a caller kwarg because a review template names
        one exact file, but it identifies a file, so it is a capture group."""
        assert "position" in file_scoped_placeholders()


class TestPlaceholdersIn:
    def test_finds_every_token_known_or_not(self):
        assert placeholders_in("/a/{scope}/{nonsense}/{msi_session}") == {"scope", "nonsense", "msi_session"}

    def test_ignores_non_identifier_braces(self):
        """Only identifier-shaped names count, so format specs aren't mistaken for tokens."""
        assert placeholders_in("/a/{}/{0}/{x:>3}/b") == frozenset()

    def test_handles_a_template_with_no_tokens(self):
        assert placeholders_in("/hpc/projects/group/software/test") == frozenset()

    def test_tolerates_none(self):
        assert placeholders_in(None) == frozenset()

    def test_catches_a_leftover_known_token_that_unknown_placeholders_cannot(self):
        """a resolved directory means zero tokens left.

        {run} is a legal token, so `unknown_placeholders` is blind to it surviving
        substitution
        """
        resolved = "/hpc/instruments/czii.krios1/OffloadData/24nov10/{run}_{sequence}_{tilt}_*.eer"
        assert unknown_placeholders(resolved) == frozenset()
        assert placeholders_in(resolved) == {"run", "sequence", "tilt"}


class TestUnknownPlaceholders:
    def test_flags_a_typo(self):
        assert unknown_placeholders("/a/{scop}/b") == {"scop"}


class TestMisplacedPlaceholders:
    def test_flags_a_file_scoped_token_in_a_directory_template(self):
        template = "/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/{run}_{sequence}_{tilt}_*.eer"
        assert misplaced_placeholders(template) == {"run", "sequence", "tilt"}

    def test_passes_a_pure_directory_template(self):
        assert misplaced_placeholders("/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/") == set()

    def test_ignores_unknown_tokens(self):
        """Misplacement and typos are separate reports; this one only speaks to scope."""
        assert misplaced_placeholders("/a/{scop}/b") == set()


class TestSuggestPlaceholder:
    def test_suggests_the_near_miss(self):
        assert suggest_placeholder("scop") == "scope"
        assert suggest_placeholder("msisession") == "msi_session"

    def test_returns_none_when_nothing_is_close(self):
        assert suggest_placeholder("xyzzy") is None


class TestDeclarationQuality:
    """Used for admin help text, so they cannot be blank."""

    @pytest.mark.parametrize("placeholder", PLACEHOLDERS, ids=lambda p: p.name)
    def test_every_placeholder_documents_its_source(self, placeholder):
        assert placeholder.source, f"{placeholder.token} has no source"
        assert placeholder.scope in (SESSION_SCOPED, FILE_SCOPED)

    @pytest.mark.parametrize("placeholder", PLACEHOLDERS, ids=lambda p: p.name)
    def test_token_renders_with_braces(self, placeholder):
        assert placeholder.token == "{%s}" % placeholder.name
