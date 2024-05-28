from django.contrib.auth.models import User
import sys
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umbrella.settings")
django.setup()
#from cryo_grids.models import Site, Dewar, Cane, Puck, CryoGridBox, Sample
from cryo_grids.models import *
from tem.models import *
from google.models import DriveFolder
from confluence.models import Space
from projects.models import Project
from stores.models import StaticPath,PathType, fill_place_holders

def _get_first_of(model_class):
    return model_class.objects.get(pk=1)

def create_project():
    confluence = Space.objects.create(name='BD01', space_id='CHOL', url='https://czbiohub.atlassian.net/wiki/spaces/CHOL/overview')
    drive = DriveFolder.objects.create(name='BD01', url='https://drive.google.com/drive/u/0/folders/10UfcYF1vcVJi44yMwIWjaXBjXvz8qahN')
    project = Project.objects.create(name='BD01', google_drive_folder=drive, confluence_space=confluence)
    return project

def create_grid(user):
    site = Site.objects.create(name='3400Bridge',address='3400 Bridge Parkway')
    dewar = Dewar.objects.create(name='CZII 1', site=site)
    cane = Cane.objects.create(name='cane1', color='CF1E01',dewar=dewar,position_in_dewar=1)
    puck = Puck.objects.create(name='puck1', color='CF1E01',cane=cane,position_in_cane=1)
    box = CryoGridBox.objects.create(name='box1', color='FFFFFF',puck=puck,position_in_puck=1)
    sample = Sample.objects.create(name='lysosome',ontology='GO:0005764')
    device = PlungeFreezingDevice.objects.create(name='GP2',maker_model='Leica GP2',site=site)
    plan = PlungeFreezingPlan.objects.create(sample_application_protocol = '', blot_time=6.0,wash_step='')
    plan.sample.add(sample)
    session = PlungeFreezingSession.objects.create(user=user,device=device,device_temperature=4.0,humidity=95,number_of_grids=1)
    cryo_grid = CryoGrid.objects.create(name='grid1',freezing_plan=plan,freezing_session=session,notes='test',grid_box=box)
    return cryo_grid

def create_scope_camera():
    scope = Microscope.objects.create(name='krios1')
    camera = Camera.objects.create(name='Falcon4i',root_dir='/hpc/instruments/czii.krios1/OffloadData/',initial_frame_base_dir='/OffloadData/')
    return scope, camera

def create_tem_static_path(data_type):
    if data_type in ['frames','sums','mdoc','parents','atlas']:
        instance = StaticPath.objects.create(
                data_type=data_type,
                static_path='/{workflow}/{session}/{run}/%s' % data_type,
        )
    if data_type in ['satlas']:
        # screen atlas
        instance = StaticPath.objects.create(
                data_type=data_type,
                static_path='/{workflow}/{session_group}/{grid_session}/atlas',
        )
    return instance

def create_tomo5_plan(scope, camera):
    """
    TFS tomo5 single grid tomography plan
    """
    workflow = ImagingWorkflow.objects.create(imaging_mode='tem',workflow='tomo')
    frame_path_type = PathType.objects.create(
                static_path=create_tem_static_path('frames'),
                overlay_path='/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session}/{run}_{sequence}_{tilt}_*.eer',
    )
    sum_path_type = PathType.objects.create(
                static_path=create_tem_static_path('sums'),
                overlay_path='/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session}/Batch/{run}_Exposure.mrc',
    )
    mdoc_path_type = PathType.objects.create(
                static_path=create_tem_static_path('mdoc'),
                overlay_path='/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session}/{run}.mdoc',
    )
    parent_path_type = PathType.objects.create(
                static_path=create_tem_static_path('parents'),
                overlay_path='/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session}/Batch/{run}_Search.mrc',
    )
    atlas_path_type = PathType.objects.create(
                static_path=create_tem_static_path('atlas'),
                overlay_path='/hpc/instruments/czii.{scope}/OffloadData/{workflow}/{session}/SearchMaps/{SearchMap_{date}_{timestamp}.mrc',
    )
    software = Software.objects.create(name='tomo5',
                frames=frame_path_type,
                sums=sum_path_type,
                mdocs=mdoc_path_type,
                parents=parent_path_type,
                atlas=atlas_path_type,
    )
    plan= SessionPlan.objects.create(scope=scope,camera=camera,imaging_workflow=workflow,software=software)
    return plan


def run():
    try:
        user=User.objects.get(pk=1)
    except User.DoesNotExist:
        print('Please create superuser first')
        sys.exit(1)
    grid=create_grid(User.objects.get(pk=1))
    scope,camera=create_scope_camera()
    plan=create_tomo5_plan(scope, camera)
    project=create_project()

if __name__ == "__main__":
    run()
