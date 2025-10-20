import os
import sys

import django
from cryo_grids.models import CryoGrid, CryoGridCassette
from django.contrib.auth.models import User
from tem.models import Camera, ImagingWorkflow, Microscope, SessionPlan, Software

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
#from cryo_grids.models import Site, Dewar, Cane, Puck, CryoGridBox, Sample
#from cryo_grids.models import *
from stores.models import PathType, StaticPath

#from tem.models import *


def get_scope_camera():
    scope = Microscope.objects.get(pk=1)
    camera = Camera.objects.get(pk=1)
    return scope, camera

def create_tem_static_path(data_type):
    if data_type in ['frames','sums','mdoc','parents']:
        instance = StaticPath.objects.create(
                data_type=data_type,
                static_path='/{workflow}/{msi_session}/{run}/%s' % data_type,
        )
    if data_type in ['atlas']:
        instance = StaticPath.objects.create(
            data_type=data_type,
            static_path='/{msi_session}/{run}/%s' % data_type,
        )
    if data_type in ['satlas']:
        # screen atlas
        instance = StaticPath.objects.create(
                data_type=data_type,
                static_path='/{workflow}/{session_group}/{grid_session}/atlas',
        )
    return instance

def create_multigrid_plan(scope, camera):
    """
    TFS multi grid screening plan
    """
    workflow = ImagingWorkflow.objects.create(imaging_mode='tem',workflow='scrn')
    atlas_path_type = PathType.objects.create(
                static_path=create_tem_static_path('satlas'),
                overlay_path='/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session_group}/{grid_session}/Atlas/{date}_{timestamp}.mrc',
    )
    software = Software.objects.create(name='tfs multi-grid',
                atlas=atlas_path_type,
    )
    plan= SessionPlan.objects.create(scope=scope,camera=camera,imaging_workflow=workflow,software=software)
    return plan

def place_grid_in_cassette():
    cassette = CryoGridCassette.objects.create(name='C1')
    grid = CryoGrid.objects.first()
    grid.grid_cassette = cassette
    grid.save()
    
def run():
    try:
        user=User.objects.get(pk=1)
    except User.DoesNotExist:
        print('Please create superuser first')
        sys.exit(1)
    try:
        scope,camera=get_scope_camera()
    except:
        print('Please run init first')
        sys.exit(1)
    plan=create_multigrid_plan(scope, camera)
    place_grid_in_cassette()

if __name__ == "__main__":
    run()
