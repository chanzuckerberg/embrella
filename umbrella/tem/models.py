from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from projects.models import Project
from cryo_grids.models import CryoGrid
import string
import os
import time

TEM_CHOICES = {
    'imaging mode': {
        'tem': 'TEM',
        'stem': 'STEM',
    },
    'workflow': {
        'scrn': 'Grid Screening',
        'sngl': 'Single Tilt SPA',
        'tomo': 'Tomography',
        'ptyc': 'Ptychography',
        'idpc': 'iDPC',
    }
}

# This determines file structure
TEM_COLLECTION_SOFTWARE = [
    ('epu', 'TFS EPU'),
    ('ser', 'SerialEM'),
    ('tom5', 'TFS Tomo5'),
    ('legn', 'Leginon'),
]


class Microscope(models.Model):
    '''
    Microscope determines what camera is available.
    '''
    name = models.CharField(max_length=20, default='Krios1', unique=True)

    def __str__(self):
        return self.name


class Camera(models.Model):
    '''
    Camera determines the path where frames are saved.
    '''
    name = models.CharField(max_length=20, default='Falcon4i', unique=True)
    root_dir = models.CharField(max_length=80, unique=True)
    frame_format = models.CharField(max_length=20)
    initial_frame_base_dir = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Software(models.Model):
    '''
    Software determines the paths of the output files
    '''
    name = models.CharField(max_length=50, unique=True)
    root_dir = models.CharField(max_length=200, help_text='absolute path to access images from all sessions')
    add_user_dir = models.BooleanField(help_text='need to insert username division before session')
    parent_image_dir = models.CharField(max_length=150, blank=True, null=True)
    # parent_image_pattern = models.CharField(max_length=150, blank=True, null=True)
    parent_image_prefix = models.CharField(max_length=150, blank=True, null=True)
    parent_image_suffix = models.CharField(max_length=150, blank=True, null=True)
    parent_image_file_format = models.CharField(max_length=150, blank=True, null=True)
    sum_image_dir = models.CharField(max_length=150, blank=True, null=True)
    # sum_image_pattern = models.CharField(max_length=150, blank=True, null=True)
    sum_image_prefix = models.CharField(max_length=150, blank=True, null=True)
    sum_image_suffix = models.CharField(max_length=150, blank=True, null=True)
    sum_image_file_format = models.CharField(max_length=150, blank=True, null=True)
    grid_atlas_image_dir = models.CharField(max_length=150, blank=True, null=True)
    grid_atlas_image_pattern = models.CharField(max_length=150, blank=True, null=True)
    frame_root_dir = models.CharField(max_length=150, blank=True, null=True,
                                      help_text='absolute path to access frame directory from all sessions')

    def __str__(self):
        return self.name


class ImagingWorkflow(models.Model):
    imaging_mode = models.CharField(max_length=20, choices=TEM_CHOICES['imaging mode'])
    workflow = models.CharField(max_length=20, choices=TEM_CHOICES['workflow'])

    def __str__(self):
        return '%s %s' % (self.get_imaging_mode_display(), self.get_workflow_display())


class SessionPlan(models.Model):
    scope = models.ForeignKey(Microscope, on_delete=models.CASCADE)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    imaging_workflow = models.ForeignKey(ImagingWorkflow, on_delete=models.CASCADE)
    software = models.ForeignKey(Software, on_delete=models.CASCADE)
    frame_format = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return '%s collected with %s on %s and %s' % (self.imaging_workflow, self.software, self.scope, self.camera)


class Session(models.Model):
    name = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    session_plan = models.ManyToManyField(SessionPlan, )
    grid = models.ForeignKey(CryoGrid, on_delete=models.PROTECT, null=True)
    notes = models.TextField(max_length=255, blank=True, null=True)

    def get_session_frame_glob(self):
        try:
            session_plan = self.session_plan.values()[0]
        except IndexError:
            return self.name
            # raise ValueError('get_session_frame_glob failed because no session_plan is not assigned to the session')
        session_software = Software.objects.get(pk=session_plan['software_id']
                                                )
        return os.path.join(session_software.frame_root_dir, self.name, '*.%s' % (session_plan['frame_format']))

    def get_session_sum_image_glob(self):
        try:
            session_plan = self.session_plan.values()[0]
        except IndexError:
            return self.name
            # raise ValueError('get_session_frame_glob failed because no session_plan is not assigned to the session')
        session_software = Software.objects.get(pk=session_plan['software_id']
                                                )
        return os.path.join(session_software.sum_image_dir, self.name, session_software.sum_image_pattern)

    def get_session_parent_glob(self):
        try:
            session_plan = self.session_plan.values()[0]
        except IndexError:
            return self.name
            # raise ValueError('get_session_frame_glob failed because no session_plan is not assigned to the session')
        session_software = Software.objects.get(pk=session_plan['software_id']
                                                )
        return os.path.join(session_software.parent_image_dir, self.name, session_software.parent_image_pattern)

    def get_session_atlas_glob(self):
        try:
            session_plan = self.session_plan.values()[0]
        except IndexError:
            return self.name
            # raise ValueError('get_session_frame_glob failed because no session_plan is not assigned to the session')
        session_software = Software.objects.get(pk=session_plan['software_id']
                                                )
        return os.path.join(session_software.grid_atlas_image_dir, self.name, session_software.grid_atlas_image_pattern)

    def __str__(self):
        # return self.get_session_frame_glob()
        return self.get_session_parent_glob()


def suggest_name(prefix):
    """
    Session based on prefix and then date format 24mar01.
    Make unique name by advancing to next in alphabet.
    If all are used, add one more char at the end starting from a
    """
    alphabet = string.ascii_letters
    remainders = []
    date_str = time.strftime('%y%b%d').lower()
    if prefix:
        prefix_search = prefix + date_str
    else:
        prefix_search = date_str
    used_names = list(map((lambda x: x.name), Session.objects.filter(Q(name__startswith=prefix_search))))
    if not used_names:
        # first session of the day
        return prefix_search + 'a'
    used_names = sorted(used_names, reverse=True)
    last_name = used_names[0]
    last_char = last_name[-1]
    if last_char == 'z':
        return last_name + 'a'
    else:
        try:
            my_index = alphabet.index(last_char)
            return last_name[:-1] + alphabet[my_index + 1]
        except IndexError:
            return last_name + 'a'
        except Exception:
            raise