"""Populate a demo: a handful of tomogram reviews and the wiring the
metadata-summary view needs — all pointing at the local Caddy file server.

Run:  python umbrella/manage.py runscript populate_demo
Idempotent — re-running updates the same rows instead of duplicating.

This seeds only DB rows. Pair it with your raw files under EMBRELLA_TOMODATA_DIR
(default ../.scratch/tomodata), laid out exactly as printed at the end — the
constants below ARE the path placeholders, so keep them in sync with the files
you drop on disk. Serve them with `just devup-demo` and make sure the origin of
HTTP_BASE_URL is in settings.FILESERVER_ALLOWED_HOSTS.
"""

import os
import uuid

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()

from accounts.models import SystemFeatureFlag
from django.contrib.auth import get_user_model
from processes.models import ProcPlan, ProcRun, Review, ReviewTomogram
from stores.models import Cluster, PathType
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software

# ── Demo parameters — single source of truth for DB rows AND on-disk paths ──────
# File-server base URL (served same-origin via nginx/ingress at /tomodata/). Its
# ORIGIN (scheme+host) must be in settings.FILESERVER_ALLOWED_HOSTS. Defaults to
# the local Caddy server; set EMBRELLA_DEMO_BASE_URL to the public /tomodata/ URL
# for staging (no code edit / no /admin step needed).
HTTP_BASE_URL = os.environ.get("EMBRELLA_DEMO_BASE_URL", "http://localhost:8080/tomodata/")

# Single demo login (local username/password — no self-signup). Overridable via
# env so real credentials aren't baked into the repo.
DEMO_USER = os.environ.get("EMBRELLA_DEMO_USER", "try_embrella")
DEMO_PASSWORD = os.environ.get("EMBRELLA_DEMO_PASSWORD", "demo_app")
DEMO_EMAIL = os.environ.get("EMBRELLA_DEMO_EMAIL", "demo@embrella.org")

# Scope is shared across every demo tomogram (krios1 processing tree).
SCOPE_NAME = "krios1"

# ── Per-tomogram demo specs ─────────────────────────────────────────────────────
# Each entry seeds one Review + its tomograms, plus one MsiSession + ProcRun per
# unique session_name. Add / edit / remove entries freely to curate more tomograms;
# they can have different session names, runs, positions and recon types.
# `recon_type` must be a key of _RECON below (SART, DCTF, or Denoised). Set
# `in_metadata=False` on a spec to seed the review/tomograms only (no ProcRun), so it
# does NOT appear on the metadata page — the mirror of METADATA_ONLY_RUNS below.
DEMO_TOMOGRAMS = [
    dict(
        session_name="25jul29a",
        run_id="run002",  # -> {run}
        recon_type="SART",
        positions=["Position_3"],  # one ReviewTomogram + one <pos>_Vol.zarr each
        review_name="NPC1-Deficient High-Res - SART",
        objects_of_interest="lysosome",
    ),
    # ── Edit the two entries below to point at the sessions/runs you curate ──
    dict(
        session_name="26feb20d",
        run_id="run002",
        recon_type="SART",
        positions=["Position_1", "Position_2_7", "Position_9_3"],
        review_name="PP7 virus-like particles in E. coli - SART",
        objects_of_interest="capsid protein",
    ),
    dict(
        session_name="26mar10a",
        run_id="run001",
        recon_type="DCTF",
        positions=["Position_1"],
        review_name="Crossed laser phase plate (xLPP) demonstration tomogram of single-layer apoferritin",
        objects_of_interest="",
        in_metadata=False,  # review tomograms only; don't surface on the metadata page
    ),
    dict(
        session_name="p26jun25a",
        run_id="run001",
        recon_type="DCTF",
        positions=["pt22_ts_002", "pt23_ts_001", "pt32_ts_001"],
        review_name="Crossed laser phase plate (xLPP) tomograms of E. coli overexpressing VLP",
        objects_of_interest="VLP",
        in_metadata=False,  # review tomograms only; don't surface on the metadata page
    ),
]

# Sessions/runs to surface on the metadata page WITHOUT a review or tomograms — just
# an MsiSession + ProcRun. Handy for showing rows that only have processing metadata
# (a Summary button, but nothing to review). Add dict(session_name=..., run_id=...).
METADATA_ONLY_RUNS = [
    # dict(session_name="25aug01a", run_id="run001"),
]

# reconstruction_type -> (workflow_segment, vol_suffix), mirroring the runtime
# resolution in processes/api/views.py: SART/DCTF use the aretomo3 workflow with a
# vol00x subdir; Denoised uses the denoise workflow with no vol subdir (empty
# suffix -> a "//" in the zarr path, which is expected). Thumbnails and the metadata
# summary CSV always resolve under aretomo3 regardless of recon_type.
_RECON = {
    "SART": ("aretomo3", "vol003"),
    "DCTF": ("aretomo3", "vol001"),
    "Denoised": ("denoise", ""),
}

# Flattened review/metadata URL templates: the migration-seeded versions prefix
# "{scope}.processing/" — the demo file tree drops that segment. DB-wide: every
# session in this DB resolves URLs through these (fine on a demo-only DB).
_URL_TEMPLATES = {
    "proc_url": "{http_base}{proc_software}/{msi_session}/{proc_run}/",
    "thumb_url": "{http_base}aretomo3/{msi_session}/{proc_run}/{thumb_kind}/",
    "zarr_url": "{http_base}{proc_software}/{msi_session}/{proc_run}/{vol_suffix}/{position}_Vol.zarr",
}


def run():
    for spec in DEMO_TOMOGRAMS:
        if spec["recon_type"] not in _RECON:
            raise ValueError(f"recon_type must be one of {sorted(_RECON)} (got {spec['recon_type']!r})")

    # 1) Default demo cluster. is_default=True so metadata/review fallbacks resolve
    #    to it (save() demotes any prior default).
    cluster, _ = Cluster.objects.update_or_create(
        cluster_id="demo",
        defaults=dict(
            name="Demo",
            http_base_url=HTTP_BASE_URL,
            ssh_hostname="localhost",
            is_active=True,
            is_default=True,
        ),
    )

    # 2) Flatten the migration-seeded URL templates (see _URL_TEMPLATES). Only the
    # cluster-agnostic default is rewritten; per-cluster siblings are left alone.
    for data_type, overlay in _URL_TEMPLATES.items():
        PathType.objects.filter(data_kind__data_type=data_type, cluster__isnull=True).update(overlay_path=overlay)

    # 3) Single demo login (idempotent — password re-synced from env each run).
    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username=DEMO_USER, defaults={"email": DEMO_EMAIL})
    user.email = DEMO_EMAIL
    user.is_active = True
    user.is_staff = False
    user.is_superuser = False
    user.set_password(DEMO_PASSWORD)
    user.save()

    # 4) Demo mode on — the frontend reads this flag off /user to show the home-page
    #    disclaimer (nightly reset, no cluster access). Seeded off by accounts
    #    migration 0007; enabling it here bakes it into the curated dump, so the
    #    nightly restore keeps it on without an /admin step.
    SystemFeatureFlag.objects.update_or_create(
        name="demo",
        defaults={"enabled": True, "description": "Public demo server: nightly reset, no cluster access."},
    )

    # 5) Shared session/scope chain (only session_plan is a required FK on MsiSession;
    #    user must be set — the tomograms list view formats the session owner's
    #    username). Every demo session reuses this one plan.
    scope, _ = Microscope.objects.get_or_create(name=SCOPE_NAME)
    # Key on the unique `name` and upsert, so a Falcon4i seeded by populatedbexamples
    # is altered in place instead of triggering a duplicate-name insert.
    camera, _ = Camera.objects.update_or_create(
        name="Falcon4i",
        defaults=dict(root_dir="/demo/offload", frame_format="eer", initial_frame_base_dir="/demo/frames"),
    )
    imaging_workflow, _ = ImagingWorkflow.objects.get_or_create(imaging_mode="tem", workflow="tomo")
    software, _ = Software.objects.get_or_create(name="tomo5")
    session_plan, _ = SessionPlan.objects.get_or_create(
        scope=scope, camera=camera, imaging_workflow=imaging_workflow, software=software
    )

    # 6) Proc plan is shared: both the tomograms list API and the Summary button are
    #    hard-gated on the plan name "czii-live".
    proc_plan, _ = ProcPlan.objects.get_or_create(name="czii-live")

    # 7) One Review (+ tomograms) per spec.
    for spec in DEMO_TOMOGRAMS:
        _seed_tomogram(spec, session_plan=session_plan, user=user, cluster=cluster, proc_plan=proc_plan)

    # 8) Review-less sessions/runs — just enough to appear on the metadata page.
    for spec in METADATA_ONLY_RUNS:
        msi_session = _seed_session(spec["session_name"], session_plan=session_plan, user=user)
        _seed_proc_run(msi_session, spec["run_id"], proc_plan=proc_plan)

    _print_summary()


def _seed_session(session_name, *, session_plan, user):
    """Idempotently create the MsiSession for a demo session name.

    update_or_create keeps re-runs (and specs that share a session_name) idempotent;
    user must be set — the tomograms list view formats the session owner's username.
    """
    msi_session, _ = MsiSession.objects.update_or_create(
        name=session_name, defaults=dict(session_plan=session_plan, user=user)
    )
    return msi_session


def _seed_proc_run(msi_session, run_id, *, proc_plan):
    """Idempotently create the ProcRun that surfaces a session/run on the metadata page.

    The tomograms list API and Summary button are gated on the plan name "czii-live"
    and the run name equalling run_id. A ProcRun alone (no Review/tomograms) is enough
    to make the session/run appear on the metadata page.
    """
    proc_run, _ = ProcRun.objects.get_or_create(proc_plan=proc_plan, msi_session=msi_session, name=run_id)
    return proc_run


def _seed_tomogram(spec, *, session_plan, user, cluster, proc_plan):
    """Seed the Review/ReviewTomogram rows (plus the session/run) for a single spec."""
    session_name = spec["session_name"]
    run_id = spec["run_id"]
    recon_type = spec["recon_type"]
    positions = spec["positions"]

    msi_session = _seed_session(session_name, session_plan=session_plan, user=user)
    # The ProcRun is what surfaces a session/run on the metadata page; the Review and
    # its tomograms don't need it. Set in_metadata=False for a review-only spec.
    if spec.get("in_metadata", True):
        _seed_proc_run(msi_session, run_id, proc_plan=proc_plan)

    # Review + tomograms. The (session, run_id, reconstruction_type) triple must match
    # across the Review and its tomograms; position_id feeds the zarr path.
    review, _ = Review.objects.update_or_create(
        review_name=spec["review_name"],
        defaults=dict(
            review_type="tomogram_quality",  # frontend renders this as "Tomogram Quality"
            run_id=run_id,
            reconstruction_type=recon_type,
            msi_session=msi_session,
            cluster=cluster,
            status="not_started",
            total_count=len(positions),
            reviewed_count=0,
            objects_of_interest=spec["objects_of_interest"],
        ),
    )
    for position in positions:
        ReviewTomogram.objects.update_or_create(
            # deterministic uuid5 (real syncers use uuid4) so re-runs stay idempotent
            tomogram_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"demo-{session_name}-{run_id}-{recon_type}-{position}")),
            defaults=dict(
                review=review,
                session=msi_session,
                run_id=run_id,
                reconstruction_type=recon_type,
                position_id=position,
                quality="pending",
                rejection_reasons=[],
                object_labels=[],
            ),
        )


def _print_summary():
    print(f"\nSeeded {len(DEMO_TOMOGRAMS)} demo tomogram review(s); cluster=demo (default)")
    print(f"Login: {DEMO_USER!r} (local username/password; set EMBRELLA_DEMO_PASSWORD to override)")
    print(f"Base URL: {HTTP_BASE_URL}  (origin must be in FILESERVER_ALLOWED_HOSTS)")
    print("\nDrop your raw files under EMBRELLA_TOMODATA_DIR so they resolve to:")
    for spec in DEMO_TOMOGRAMS:
        session_name = spec["session_name"]
        run_id = spec["run_id"]
        workflow, vol_suffix = _RECON[spec["recon_type"]]
        # Thumbnails + the metadata summary CSV always live under aretomo3; only the
        # review zarr uses the recon-derived workflow segment (+ vol subdir).
        thumb_base = f"aretomo3/{session_name}/{run_id}"
        zarr_base = f"{workflow}/{session_name}/{run_id}"
        # Denoised has an empty vol_suffix -> the zarr sits directly under the run dir
        # (no vol subfolder). The resolved URL has a "//" there, but nginx merges
        # slashes before serving, so on disk it's a single slash — drop the file here.
        vol_seg = f"{vol_suffix}/" if vol_suffix else ""
        tag = "" if spec.get("in_metadata", True) else "  (review-only, not on metadata page)"
        print(f"\n  [{spec['review_name']}]  session={session_name} run={run_id} recon={spec['recon_type']}{tag}")
        # Metadata summary + thumbnails only matter for specs shown on the metadata page.
        if spec.get("in_metadata", True):
            print(f"    metadata summary : {thumb_base}/TiltSeries_Metrics.csv")
            print(f"    parameters       : {thumb_base}/AreTomo3_Session.json")
            print(f"    thumbnail grid   : {thumb_base}/thumbnails/<Tilt_Series>.jpeg")
            print(f"                       {thumb_base}/ctf_thumbnails/<Tilt_Series>.jpeg")
        for position in spec["positions"]:
            print(f"    review zarr      : {zarr_base}/{vol_seg}{position}_Vol.zarr/")
    for spec in METADATA_ONLY_RUNS:
        base = f"aretomo3/{spec['session_name']}/{spec['run_id']}"
        print(f"\n  [metadata-only]  session={spec['session_name']} run={spec['run_id']}")
        print(f"    metadata summary : {base}/TiltSeries_Metrics.csv")
        print(f"    parameters       : {base}/AreTomo3_Session.json")
        print(f"    thumbnail grid   : {base}/thumbnails/<Tilt_Series>.jpeg")
    print("\nView:")
    print("  tomograms: http://localhost:8080/processing/tomograms/metadata (rows with a Summary button)")
    print("  metadata : http://localhost:8080/metadata/view/<session>/<run>")
    print("  review   : http://localhost:8080/processing (open a review, then a tomogram)")


if __name__ == "__main__":
    run()
