"""Job scripts render their remote paths from the DB templates, not literals.

Each processor's render_script resolves its trees (processing root, script dir, shared
software tree, session mdoc dir) and the rendered bash follows -- so moving a template
row moves every script, and a second scope needs zero template edits.
"""

import pytest
from django.contrib.auth.models import User
from processes.models import ProcSoftware
from stores.models import DataKind, PathType
from tem.models import Camera, ImagingWorkflow, Microscope, MsiSession, SessionPlan, Software
from workflow.context import RunContext
from workflow.processors import get_processor

pytestmark = pytest.mark.django_db

PROCESSING_ROOT = "/hpc/projects/group.czii/krios1.processing"


@pytest.fixture
def session(db):
    """A session on scope krios1 whose plan binds an mdoc directory template."""
    mdoc_kind, _ = DataKind.objects.get_or_create(data_type="mdoc")
    plan = SessionPlan.objects.create(
        scope=Microscope.objects.create(name="krios1", cs=2.7),
        camera=Camera.objects.create(
            name="TestCamera",
            root_dir="/test/root",
            frame_format="eer",
            initial_frame_base_dir="/test/frames",
        ),
        imaging_workflow=ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo"),
        software=Software.objects.create(
            name="TestSoftware",
            mdocs=PathType.objects.create(
                data_kind=mdoc_kind,
                overlay_path="/instruments/{scope}/offload/{msi_session}/",
            ),
        ),
    )
    return MsiSession.objects.create(name="24nov10", session_plan=plan)


@pytest.fixture
def software_rows(db):
    """The ProcSoftware rows the roots resolve {proc_software} from."""
    for processor_class, name in (("aretomo3", "aretomo3"), ("denoiset", "denoise"), ("copick", "copick")):
        ProcSoftware.objects.update_or_create(processor_class=processor_class, defaults={"name": name})


@pytest.fixture
def run_context(session, software_rows):
    return RunContext(
        proc_run=None,  # render_script reads session/run/user only
        pipe_in_plan=None,
        msi_session=session,
        user=User.objects.create_user(username="testuser"),
        cluster_id="czii",
        run_number="run001",
        job_name="test_job",
        inputs={},
    )


ARETOMO3_PARAMS = {"pixel_size": 2.0, "frame_dose": 1.5, "gain_file_name": "gain.gain"}


class TestAretomo3Script:
    def test_output_tree_is_the_processing_root(self, run_context):
        script = get_processor("aretomo3").render_script(dict(ARETOMO3_PARAMS), run_context)

        out_dir = f"{PROCESSING_ROOT}/aretomo3/24nov10/run001"
        assert f'export out_path="{out_dir}"' in script
        assert f"#SBATCH -o {out_dir}/JOB%j_aretomo3.out" in script
        assert f"#SBATCH -e {out_dir}/JOB%j_reformat.err" in script

    def test_mdoc_dir_is_the_sessions(self, run_context):
        script = get_processor("aretomo3").render_script(dict(ARETOMO3_PARAMS), run_context)

        assert 'export in_mdoc_dir="/instruments/krios1/offload/24nov10"' in script

    def test_tool_trees_resolve(self, run_context):
        script = get_processor("aretomo3").render_script(dict(ARETOMO3_PARAMS), run_context)

        assert f"conda activate {PROCESSING_ROOT}/aretomo3/scripts/zarrczar_env" in script
        assert f"{PROCESSING_ROOT}/software/executables/AreTomo3_" in script
        assert f"python {PROCESSING_ROOT}/software/diagnostics/scripts/plot_aretomo3_metrics.py" in script

    def test_editing_the_template_moves_the_script(self, run_context):
        """The point of the change: the row is the one source of the tree."""
        PathType.objects.filter(data_kind__data_type="processing_root").update(
            overlay_path="/data/runs/{proc_software}"
        )
        script = get_processor("aretomo3").render_script(dict(ARETOMO3_PARAMS), run_context)

        assert 'export out_path="/data/runs/aretomo3/24nov10/run001"' in script

    def test_session_without_mdocs_fails_loudly(self, run_context):
        """A silently rendered "." would submit a job reading the cwd."""
        software = run_context.msi_session.session_plan.software
        software.mdocs = None
        software.save()

        with pytest.raises(ValueError, match="no mdocs directory"):
            get_processor("aretomo3").render_script(dict(ARETOMO3_PARAMS), run_context)


class TestCopickScript:
    CREATE_PARAMS = {"operation": "create", "import_tomo_type": "dctf", "import_tomogram_run": "run001"}

    def test_project_dir_is_copicks_root(self, run_context):
        script = get_processor("copick").render_script(dict(self.CREATE_PARAMS), run_context)

        assert f'copick_dir="{PROCESSING_ROOT}/copick/${{session}}/${{copick_procrun}}"' in script

    def test_tomo_paths_resolve_through_the_owning_software(self, run_context):
        """dctf/sart/wbp read aretomo3's tree; denoise reads denoiset's `denoise` dirname."""
        script = get_processor("copick").render_script(dict(self.CREATE_PARAMS), run_context)

        assert f'tomo_path="{PROCESSING_ROOT}/aretomo3/${{session}}/${{tomo_run}}/vol001/*.mrc"' in script
        assert f'tomo_path="{PROCESSING_ROOT}/denoise/${{session}}/${{tomo_run}}/*.mrc"' in script

    def test_add_object_shares_the_root(self, run_context):
        params = {
            "operation": "add_object",
            "copick_session": "24nov10",
            "copick_run": "run001",
            "object_name": "ribosome",
            "object_diameter": 250,
            "template_map_name": "ribosome",
        }
        script = get_processor("copick").render_script(params, run_context)

        assert f'template_maps_dir="{PROCESSING_ROOT}/copick/template_maps"' in script
        assert f'copick_base_dir="{PROCESSING_ROOT}/copick/${{copick_session}}/${{copick_run}}"' in script


class TestDenoisetScript:
    def test_trees_resolve_per_owner(self, run_context):
        script = get_processor("denoiset").render_script({"aretomo_run": "run001", "model_name": "m.pth"}, run_context)

        assert f'in_dir="{PROCESSING_ROOT}/aretomo3/${{session}}/${{aretomo_run}}/vol001"' in script
        assert f'out_dir="{PROCESSING_ROOT}/denoise/${{session}}/${{denoise_run}}"' in script
        assert f'model="{PROCESSING_ROOT}/software/denoiset/denoiset/models/${{model_name}}"' in script
        assert f"bash {PROCESSING_ROOT}/denoise/scripts/rechunk.sh" in script


class TestMembranesegScript:
    def test_copick_tree_resolves_through_copick(self, run_context):
        params = {
            "copick_session": "24nov10",
            "copick_procrun": "run001",
            "tomo_type": "dctf",
            "tomo_voxel_size": 10.0,
        }
        script = get_processor("membraneseg").render_script(params, run_context)

        assert f'copick_dir="{PROCESSING_ROOT}/copick/${{session}}/${{copick_procrun}}"' in script
