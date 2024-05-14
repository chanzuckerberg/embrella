from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from projects.models import Project
from cryo_grids.models import CryoGrid
from stores.models import Path, PathType, fill_place_holders
import os
import time
import string
from pydantic import BaseModel
from typing import List, Union, Optional

TEM_CHOICES = {
    'imaging_mode': [
        ('tem', 'TEM'),
        ('stem', 'STEM'),
    ],
    'workflow': [
        ('scrn', 'Grid Screening'),
        ('sngl', 'Single Tilt SPA'),
        ('tomo', 'Tomography'),
        ('ptyc', 'Ptychography'),
        ('idpc', 'iDPC'),
        ('clem', 'CLEM Mapping'),
    ]
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

    class Meta:
        app_label = 'tem'


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

    class Meta:
        app_label = 'tem'


class Software(models.Model):
    '''
    Software determines the paths of the output files
    '''
    name = models.CharField(max_length=50, unique=True)
    frames = models.ForeignKey(PathType, related_name='frames_type', on_delete=models.SET_NULL, null=True,
                               help_text='path pattern to access frames')
    sums = models.ForeignKey(PathType, related_name='sums_type', on_delete=models.SET_NULL, null=True,
                             help_text='path pattern to access 0 tilt projection thumbnail image')
    mdocs = models.ForeignKey(PathType, related_name='mdocs_type', on_delete=models.SET_NULL, null=True,
                              help_text='path pattern to access mdocs')

    parents = models.ForeignKey(PathType, related_name='parents_type', on_delete=models.SET_NULL, null=True,
                                help_text='path pattern to access parent images for viewing')
    atlas = models.ForeignKey(PathType, related_name='atlas_type', on_delete=models.SET_NULL, null=True,
                              help_text='path pattern to access grid atlas image for viewing')

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'tem'


class ImagingWorkflow(models.Model):
    imaging_mode = models.CharField(max_length=20, choices=TEM_CHOICES['imaging_mode'])
    workflow = models.CharField(max_length=20, choices=TEM_CHOICES['workflow'])

    def __str__(self):
        return '%s %s' % (self.get_imaging_mode_display(), self.get_workflow_display())


class SessionPlan(models.Model):
    scope = models.ForeignKey(Microscope, on_delete=models.CASCADE)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE)
    imaging_workflow = models.ForeignKey(ImagingWorkflow, on_delete=models.CASCADE)
    software = models.ForeignKey(Software, on_delete=models.CASCADE)

    def __str__(self):
        return '%s collected with %s on %s and %s' % (self.imaging_workflow, self.software, self.scope, self.camera)

    class Meta:
        app_label = 'tem'


class Session(models.Model):
    name = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    grid = models.ForeignKey(CryoGrid, on_delete=models.PROTECT, null=True)
    notes = models.TextField(max_length=255, blank=True, null=True)
    frames = models.ForeignKey(Path, related_name='frames', on_delete=models.SET_NULL, null=True)
    mdocs = models.ForeignKey(Path, related_name='mdocs', on_delete=models.SET_NULL, null=True)
    sums = models.ForeignKey(Path, related_name='sums', on_delete=models.SET_NULL, null=True)
    parents = models.ForeignKey(Path, related_name='parents', on_delete=models.SET_NULL, null=True)
    atlas = models.ForeignKey(Path, related_name='atlas', on_delete=models.SET_NULL, null=True)

    class Meta:
        app_label = 'tem'

    def _get_session_glob(self, path_type):
        plan = self.session_plan
        scope_name = plan.scope.name
        my_attr = getattr(plan.software, path_type)
        if not my_attr:
            out_path = '.'
        else:
            out_path = fill_place_holders(my_attr.overlay_path,
                                            {
                                                'workflow': plan.imaging_workflow.workflow,
                                                'scope': scope_name,
                                                'session': self.name
                                          }
                                          )
            return out_path

    def get_session_frames_glob(self):
        return self._get_session_glob('frames')

    def get_session_mdocs_glob(self):
        return self._get_session_glob('mdocs')

    def get_session_sums_glob(self):
        return self._get_session_glob('sums')

    def get_session_parents_glob(self):
        return self._get_session_glob('parents')

    def get_session_atlas_glob(self):
        return self._get_session_glob('atlas')

    def get_session_path(self, type_name='frames'):
        """
        Use session_plan and software to update session path by replacing place holders
        """
        plan = self.session_plan
        scope_name = plan.scope.name
        path_obj = getattr(plan.software, type_name)
        static_path = fill_place_holders(path_obj.static_path,
                                         {
                                             'workflow': plan.imaging_workflow.workflow,
                                             'scope': scope_name,
                                             'session': self.name
                                         }
                                         )
        session_attr = getattr(self, 'get_session_%s_glob' % type_name)
        overlay_path = fill_place_holders(session_attr(),
                                          {
                                              'workflow': plan.imaging_workflow.workflow,
                                              'scope': scope_name,
                                              'session': self.name
                                          }
                                          )
        path_set = Path.objects.filter(overlay_path=overlay_path, static_path=static_path)
        if not path_set:
            p = Path(overlay_path=overlay_path, static_path=static_path)
            p.save()
        else:
            p = path_set[0]
        return p

    def __str__(self):
        return self.get_session_sums_glob()


class PathInfo(BaseModel):
    static_path: str | None
    overlay_path: str | None

class SoftwareFieldsResponse(BaseModel):
    name: str
    frames: PathInfo
    sums: PathInfo
    mdocs: PathInfo
    parents: PathInfo
    atlas: PathInfo


class SoftwareResponseModel(BaseModel):
    model: str
    pk: int  # redundant info
    fields: SoftwareFieldsResponse

class ErrorResponse(BaseModel):
    error: str


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
