"""The placeholder table -- no logic."""

from dataclasses import dataclass

# Placeholder.scope values.
SESSION_SCOPED = "session"
FILE_SCOPED = "file"


@dataclass(frozen=True)
class Placeholder:
    """One `{token}`."""

    name: str
    scope: str
    source: str
    notes: str = ""

    def __post_init__(self):
        if self.scope not in (SESSION_SCOPED, FILE_SCOPED):
            raise ValueError(f"scope must be {SESSION_SCOPED!r} or {FILE_SCOPED!r}, got {self.scope!r}")

    @property
    def token(self):
        return "{%s}" % self.name


PLACEHOLDERS = (
    # -- Session-scoped: supplied by a replacement map, substituted into the directory --
    Placeholder(
        "scope",
        SESSION_SCOPED,
        "the session's Microscope.name",
        notes="Used verbatim. Name the scope exactly as its directory is spelled.",
    ),
    Placeholder("msi_session", SESSION_SCOPED, "MsiSession.name"),
    Placeholder(
        "workflow",
        SESSION_SCOPED,
        "session_plan.imaging_workflow.workflow",
        notes="The imaging workflow -- tomo/scrn/sngl/clem.",
    ),
    Placeholder("session_group", SESSION_SCOPED, "AtlasSession.group.name", notes="Atlas templates only."),
    Placeholder("atlas_session", SESSION_SCOPED, "AtlasSession.name", notes="Atlas templates only."),
    Placeholder("camera", SESSION_SCOPED, "session_plan.camera.name"),
    Placeholder(
        "frame_format",
        SESSION_SCOPED,
        "session_plan.camera.frame_format",
        notes="eer/tiff/mrc -- what keeps a camera difference from needing a config row.",
    ),
    Placeholder("root_dir", SESSION_SCOPED, "session_plan.camera.root_dir", notes="Trailing slash stripped."),
    Placeholder(
        "initial_frame_base_dir",
        SESSION_SCOPED,
        "session_plan.camera.initial_frame_base_dir",
        notes="Trailing slash stripped.",
    ),
    Placeholder("proc_software", SESSION_SCOPED, "pipe.software.name", notes="e.g. aretomo3, denoiset, copick."),
    Placeholder("proc_run", SESSION_SCOPED, "ProcRun.name", notes="e.g. run001. This is the processing run."),
    Placeholder("proc_plan", SESSION_SCOPED, "ProcPlan.name"),
    Placeholder("pipe", SESSION_SCOPED, "Pipe.name", notes="e.g. vol001."),
    Placeholder(
        "cluster",
        SESSION_SCOPED,
        "RunContext.cluster_id",
        notes="hpc cluster used",
    ),
    Placeholder("http_base", SESSION_SCOPED, "Cluster.http_base_url", notes="Review URL templates only."),
    Placeholder("thumb_kind", SESSION_SCOPED, 'caller kwarg -- "thumbnails" or "ctf_thumbnails"'),
    Placeholder(
        "vol_suffix",
        SESSION_SCOPED,
        "for aretomo volumes: vol001/vol003, empty for denoised",
    ),
    Placeholder("copick_run", SESSION_SCOPED, "caller kwarg -- ProcRun.name for a copick project"),
    # -- File-scoped: unknowable at create time, so they are capture groups, not substitutions --
    Placeholder(
        "run",
        FILE_SCOPED,
        "capture group",
        notes="A tilt-series id or acquisition position within a filename.",
    ),
    Placeholder("sequence", FILE_SCOPED, "capture group", notes="frames filenames."),
    Placeholder("tilt", FILE_SCOPED, "capture group", notes="frames filenames."),
    Placeholder("run_stage_pos", FILE_SCOPED, "capture group", notes="sums and parents filenames."),
    Placeholder("timestamp", FILE_SCOPED, "capture group", notes="atlas and gain filenames; gain sorts by it."),
    Placeholder("date", FILE_SCOPED, "capture group", notes="satlas filenames."),
    Placeholder(
        "position",
        FILE_SCOPED,
        "capture group",
        notes="e.g. Position_1_2, from a reconstruction filename. Review templates name one "
        "exact file, so they pre-substitute it from a caller kwarg rather than capturing it.",
    ),
)
