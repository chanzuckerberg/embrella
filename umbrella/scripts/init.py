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
    sample = Sample.objects.create(name='lysosome')
    device = PlungeFreezingDevice.objects.create(name='lysosome',maker_model='Leica GP2',site=site)
    plan = PlungeFreezingPlan.objects.create(sample_application_protocol = '', blot_time=6.0,wash_step='',tag='no tag')
    plan.sample.add(sample)
    session = PlungeFreezingSession.objects.create(user=user,device=device,device_temperature=4.0,humidity=95,number_of_grids=1)
    cryo_grid = CryoGrid.objects.create(name='grid1',freezing_plan=plan,freezing_session=session,notes='test',grid_box=box)
    return cryo_grid

def create_tomo5_plan(grid):
    camera = Camera.objects.create(name='Falcon4i',root_dir='/hpc/instruments/czii.krios1/OffloadData/',frame_format='eer',initial_frame_base_dir='/OffloadData/')
    scope = Microscope.objects.create(name='Krios1')
    workflow = ImagingWorkflow.objects.create(imaging_mode='tem',workflow='tomo')
    software = Software.objects.create(name='tom5',
                image_root_dir='/hpc/instruments/czii.krios1/OffloadData/',
                frame_root_dir='/hpc/instruments/czii.krios1/OffloadData/',
                parent_image_dir='Batch/',
                sum_image_dir='Batch/',
                sum_image_pattern='*_Exposure.mrc',
                parent_image_pattern='*_Search.mrc',
                grid_atlas_image_pattern='SearchMap*.mrc',
                grid_atlas_image_dir='SearchMaps/',
                add_user_dir=False,
    )
    plan= SessionPlan.objects.create(scope=scope,camera=camera,imaging_workflow=workflow,software=software,frame_format='eer')
    return plan

def run():
    try:
        user=User.objects.get(pk=1)
    except User.DoesNotExist:
        print('Please create superuser first')
        sys.exit(1)
    grid=create_grid(User.objects.get(pk=1))
    plan=create_tomo5_plan(grid)
    project=create_project()

run()