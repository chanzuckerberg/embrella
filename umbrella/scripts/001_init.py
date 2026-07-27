import os
import sys

import django
from django.contrib.auth.models import User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
# from cryo_grids.models import Site, Dewar, Cane, Puck, CryoGridBox, Sample
# from cryo_grids.models import *
from cryo_grids.models import (
    Cane,
    CryoGrid,
    CryoGridBox,
    Dewar,
    PlungeFreezingDevice,
    PlungeFreezingSession,
    Puck,
    Sample,
    Site,
    Specimen,
)
from external_links.models import ExternalResource
from projects.models import Project
from stores.models import PathType, StaticPath

# from tem.models import *
from tem.models import Camera, ImagingWorkflow, Microscope, SessionPlan, Software
from umbrella.choices import PUCK_COLORS


def _get_first_of(model_class):
    return model_class.objects.get(pk=1)


def create_project():
    # Create ExternalResource for documentation space
    external_confluence = ExternalResource.objects.create(
        resource_type="doc_space",
        system_name="Confluence",
        name="BD01",
        url="https://czbiohub.atlassian.net/wiki/spaces/CHOL/overview",
        metadata={"space_id": "CHOL"},
    )

    # Create project with unified documentation field
    project = Project.objects.create(name="BD01", documentation_space=external_confluence)
    return project


def create_sample():
    sample = Sample.objects.create(name="lysosome", ontology="GO:0005764")
    return sample


def create_grid(user, project, sample_input):
    site = Site.objects.create(name="3400Bridge", address="3400 Bridge Parkway")
    dewar = Dewar.objects.create(name="CZII 1", site=site)
    dewar2 = Dewar.objects.create(name="CZII 2", site=site)

    cane = Cane.objects.create(name="cane1", color="CF1E01", dewar=dewar, position_in_dewar=1)
    cane2 = Cane.objects.create(name="cane2", color="FFC0CB", dewar=dewar2, position_in_dewar=1)

    puck = Puck.objects.create(name="puck1", color=PUCK_COLORS[0][0], cane=cane, position_in_cane=1)
    for i in range(2, 11):
        Puck.objects.create(name=f"puck{i}", color=PUCK_COLORS[i - 1][0], cane=cane, position_in_cane=i)
    for i in range(11, 21):
        Puck.objects.create(name=f"puck{i}", color=PUCK_COLORS[i - 11][0], cane=cane2, position_in_cane=i - 10)

    box = CryoGridBox.objects.create(name="box1", color="FFFFFF", puck=puck, position_in_puck=1)
    # specimen = Specimen.objects.create(samples=sample_input,notes='')
    specimen = Specimen.objects.create(notes="")
    specimen.samples.set([sample_input])  # Wrap the object in a list
    device = PlungeFreezingDevice.objects.create(name="GP2", maker_model="Leica GP2", site=site)
    device_vitrobot = PlungeFreezingDevice.objects.create(name="Vitrobot", maker_model="Vitrobot", site=site)
    session = PlungeFreezingSession.objects.create(user=user, device=device, device_temperature=4.0, humidity=95)
    cryo_grid = CryoGrid.objects.create(
        name="grid1",
        specimen=specimen,
        freezing_session=session,
        notes="test",
        grid_box=box,
        user=user,
        intended_project=project,
        blot_time=6.0,
        blot_force=0.0,
        blot_distance=0.0,
    )
    return cryo_grid


def create_scope_camera():
    scope = Microscope.objects.create(name="krios1")
    camera = Camera.objects.create(
        name="Falcon4i", root_dir="/hpc/instruments/czii.krios1/OffloadData/", initial_frame_base_dir="/OffloadData/"
    )
    return scope, camera


def create_tem_static_path(data_type):
    if data_type in ["frames", "sums", "mdoc", "parents", "atlas"]:
        instance = StaticPath.objects.create(
            data_type=data_type,
            static_path="/{workflow}/{msi_session}/{run}/%s" % data_type,
        )
    if data_type in ["satlas"]:
        # screen atlas
        instance = StaticPath.objects.create(
            data_type=data_type,
            static_path="/{workflow}/{session_group}/{grid_session}/atlas",
        )
    return instance


def create_tomo5_plan(scope, camera):
    """
    TFS tomo5 single grid tomography plan
    """
    workflow = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="tomo")
    frame_path_type = PathType.objects.create(
        static_path=create_tem_static_path("frames"),
        overlay_path="/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/{run}_{sequence}_{tilt}_*.eer",
    )
    sum_path_type = PathType.objects.create(
        static_path=create_tem_static_path("sums"),
        overlay_path="/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{msi_session}/Batch/{run_stage_pos}_Exposure.mrc",
    )
    mdoc_path_type = PathType.objects.create(
        static_path=create_tem_static_path("mdoc"),
        overlay_path="/hpc/instruments/czii.{scope}/OffloadData/{msi_session}/{run}.mdoc",
    )
    parent_path_type = PathType.objects.create(
        static_path=create_tem_static_path("parents"),
        overlay_path="/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{msi_session}/Batch/{run_stage_pos}_Search.mrc",
    )
    atlas_path_type = PathType.objects.create(
        static_path=create_tem_static_path("atlas"),
        overlay_path="/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session_group}/{atlas_session}/Atlas/Atlas_{timestamp}.mrc",
    )
    software = Software.objects.create(
        name="tomo5",
        frames=frame_path_type,
        sums=sum_path_type,
        mdocs=mdoc_path_type,
        parents=parent_path_type,
        atlas=atlas_path_type,
    )
    plan = SessionPlan.objects.create(scope=scope, camera=camera, imaging_workflow=workflow, software=software)
    return plan


def run():
    try:
        user = User.objects.get(pk=1)
    except User.DoesNotExist:
        print("Please create superuser first")
        sys.exit(1)
    project = create_project()
    sample = create_sample()
    grid = create_grid(User.objects.get(pk=1), project, sample)
    scope, camera = create_scope_camera()
    plan = create_tomo5_plan(scope, camera)


if __name__ == "__main__":
    run()
