import os
import sys

import django
from cryo_grids.models import CryoGrid, CryoGridCassette
from django.contrib.auth.models import User
from tem.models import Camera, ImagingWorkflow, Microscope, SessionPlan, Software

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
# from cryo_grids.models import Site, Dewar, Cane, Puck, CryoGridBox, Sample
# from cryo_grids.models import *
from stores.models import DataKind, FilePattern, PathType

# from tem.models import *


def get_scope_camera():
    scope = Microscope.objects.get(pk=1)
    camera = Camera.objects.get(pk=1)
    return scope, camera


def create_tem_data_kind(data_type):
    # Branched by data_type until the vestigial static_path template came off DataKind;
    # every kind is now just its name.
    return DataKind.objects.create(data_type=data_type)


def create_multigrid_plan(scope, camera):
    """
    TFS multi grid screening plan
    """
    workflow = ImagingWorkflow.objects.create(imaging_mode="tem", workflow="scrn")
    data_kind = create_tem_data_kind("satlas")
    atlas_path_type = PathType.objects.create(
        data_kind=data_kind,
        overlay_path="/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session_group}/{atlas_session}/Atlas/",
        # Same directory as tomo5's atlas, different filenames -- which is the split
        file_pattern=FilePattern.objects.create(
            data_kind=data_kind,
            label="{date}_{timestamp}.mrc",
            list_glob="*.mrc",
            regex=r"^(?P<date>[\d-]+)_(?P<timestamp>[\w-]+)\.mrc$",
        ),
    )
    software = Software.objects.create(
        name="tfs multi-grid",
        atlas=atlas_path_type,
    )
    plan = SessionPlan.objects.create(scope=scope, camera=camera, imaging_workflow=workflow, software=software)
    return plan


def place_grid_in_cassette():
    cassette = CryoGridCassette.objects.create(name="C1")
    grid = CryoGrid.objects.first()
    grid.grid_cassette = cassette
    grid.save()


def run():
    try:
        user = User.objects.get(pk=1)
    except User.DoesNotExist:
        print("Please create superuser first")
        sys.exit(1)
    try:
        scope, camera = get_scope_camera()
    except:
        print("Please run init first")
        sys.exit(1)
    plan = create_multigrid_plan(scope, camera)
    place_grid_in_cassette()


if __name__ == "__main__":
    run()
