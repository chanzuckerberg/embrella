from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.validators import validate_comma_separated_integer_list

from projects.models import Project
from cryo_grids.models import CryoGrid, CryoGridCassette
from stores.models import Path, PathType, fill_place_holders
import sys
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
    frames = models.ForeignKey(PathType, related_name='frames_type', on_delete=models.SET_NULL, null=True, blank=True,
                               help_text='path pattern to access frames')
    sums = models.ForeignKey(PathType, related_name='sums_type', on_delete=models.SET_NULL, null=True, blank=True,
                             help_text='path pattern to access 0 tilt projection thumbnail image')
    mdocs = models.ForeignKey(PathType, related_name='mdocs_type', on_delete=models.SET_NULL, null=True, blank=True,
                              help_text='path pattern to access mdocs')

    parents = models.ForeignKey(PathType, related_name='parents_type', on_delete=models.SET_NULL, null=True, blank=True,
                                help_text='path pattern to access parent images for viewing')
    atlas = models.ForeignKey(PathType, related_name='atlas_type', on_delete=models.SET_NULL, null=True, blank=True,
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

class ScreenSessionGroup(models.Model):
    """
    A grouping of screening on grids. It is identified by the cassette
    and the order of the grid positions that are loaded and imaged.
    """
    name = models.CharField(max_length=20, unique=True)
    cassette = models.ForeignKey(CryoGridCassette, on_delete=models.PROTECT, null=True)
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    order = models.CharField(max_length=36, validators=[validate_comma_separated_integer_list], help_text='comma separated list ofgrid positions to screen, i.e. 1,2,5', default='1,2,3,4,5,6,7,8,9,10,11,12')

    def get_order_list(self):
        try:
            return parse_integer_order_list(self.order)
        except Exception as e:
            raise ValueError('Bad order field entry: %s' % e)

    def __str__(self):
        return '%s - Screening of %s' % (self.name, self.cassette)

class AtlasSession(models.Model):
    """
    A tem session which purpose is to assess the quality of the grid.
    Currently only record atlas path.
    """
    # name is determined by software
    name = models.CharField(max_length=20, unique=False, help_text="software-dependent name for the screen session for the grid")
    group = models.ForeignKey(ScreenSessionGroup, on_delete=models.CASCADE)
    order_in_screen = models.PositiveSmallIntegerField(default=1)
    grid = models.ForeignKey(CryoGrid, on_delete=models.PROTECT, null=True)
    atlas = models.ForeignKey(Path, related_name='screenatlas', on_delete=models.SET_NULL, null=True)
    quality = models.SmallIntegerField(
            default=-1,
            help_text='grid quality score 0-5 5=highest, -1=not started, 0=failed'
    )
    notes = models.TextField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = [["name","group"]]
        constraints = [
            models.CheckConstraint(check=models.Q(quality__lte=5),name='quality_score_exceed_max'),
            models.CheckConstraint(check=models.Q(quality__gte=-1),name='quality_score_not_valid')
        ]
 
    def get_replacement_map(self):
        plan = self.group.session_plan
        scope_name = plan.scope.name
        mapping = {
            'workflow': plan.imaging_workflow.workflow,
            'scope': scope_name,
            'session_group': self.group.name,
            'atlas_session': self.name,
        }
        return mapping

    def _get_session_glob(self, path_type):
        plan = self.group.session_plan
        my_attr = getattr(plan.software, path_type)
        if not my_attr:
            out_path = '.'
        else:
            out_path = fill_place_holders(my_attr.overlay_path,
                    self.get_replacement_map()
            )
            return out_path

    def get_session_path(self, type_name='atlas'):
        """
        Use session_plan and software to update session path by replacing place holders
        """
        plan = self.group.session_plan
        path_obj = getattr(plan.software, type_name)
        static_path = fill_place_holders(path_obj.static_path.static_path,
                    self.get_replacement_map()
        )
        session_attr = getattr(self, 'get_session_%s_glob' % type_name)
        overlay_path = fill_place_holders(session_attr(),
                    self.get_replacement_map()
        )
        path_set = Path.objects.filter(overlay_path=overlay_path, static_path=static_path)
        if not path_set:
            p = Path(overlay_path=overlay_path, static_path=static_path)
            p.save()
        else:
            p = path_set[0]
        return p

    def get_session_atlas_glob(self):
        return self._get_session_glob('atlas')

    def __str__(self):
        return '/scrn/%s/%s/' % (self.group.name,self.name)


class MsiSession(models.Model):
    '''
    Multi-scale imaging session
    '''
    name = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True)
    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE)
    grid = models.ForeignKey(CryoGrid, on_delete=models.PROTECT, null=True)
    notes = models.TextField(max_length=255, blank=True, null=True)
    frames = models.ForeignKey(Path, related_name='frames', on_delete=models.SET_NULL, null=True, blank=True)
    mdocs = models.ForeignKey(Path, related_name='mdocs', on_delete=models.SET_NULL, null=True, blank=True)
    sums = models.ForeignKey(Path, related_name='sums', on_delete=models.SET_NULL, null=True, blank=True)
    parents = models.ForeignKey(Path, related_name='parents', on_delete=models.SET_NULL, null=True, blank=True)
    atlas = models.ForeignKey(Path, related_name='atlas', on_delete=models.SET_NULL, null=True, blank=True)
    atlas_session = models.ForeignKey(AtlasSession, on_delete=models.SET_NULL, null=True,blank=True, help_text='link a seperate grid screen atlas if exists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
                                                'msi_session': self.name
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
        if self.atlas_session:
            # grid screening of this grid exists
            return self.atlas_session._get_session_glob('atlas')
        else:
            return self._get_session_glob('atlas')

    def get_session_path(self, type_name='frames'):
        """
        Use session_plan and software to update session path by replacing place holders
        """
        plan = self.session_plan
        scope_name = plan.scope.name
        path_obj = getattr(plan.software, type_name)
        static_path = fill_place_holders(path_obj.static_path.static_path,
                                         {
                                             'workflow': plan.imaging_workflow.workflow,
                                             'scope': scope_name,
                                             'msi_session': self.name
                                         }
                                         )
        session_attr = getattr(self, 'get_session_%s_glob' % type_name)
        overlay_path = fill_place_holders(session_attr(),
                                          {
                                              'workflow': plan.imaging_workflow.workflow,
                                              'scope': scope_name,
                                              'msi_session': self.name
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
        return 'msi %s' % self.name

def parse_integer_order_list(text):
    return list((map((lambda x: int(x)), text.split(','))))

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

class UserBase(BaseModel):
    username: str

class ProjectBase(BaseModel):
    name: str

class MsiSessionBase(BaseModel):
    id: int
    name: str
    notes: str
    user: UserBase
    project: ProjectBase
    frames: PathInfo
    mdocs: PathInfo
    sums: PathInfo
    parents: PathInfo
    atlas: PathInfo

def suggest_name(prefix, model_name='MsiSession'):
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
    model_instance = getattr(sys.modules[__name__], model_name)
    used_names = list(map((lambda x: x.name), model_instance.objects.filter(Q(name__startswith=prefix_search))))
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

def suggest_scrn_session_name(prefix,group_instance):
    model_instance = AtlasSession
    used_names = list(map((lambda x: x.name), model_instance.objects.filter(Q(group=group_instance,name__startswith=prefix))))
    software = group_instance.session_plan.software
    # TODO need to find a way to decide whether names are defined as Sample%d
    if software.name == 'tfs multi-grid':
        return 'Sample%d' % (len(used_names)+1,)
    else:
        return suggest_name(prefix, model_name='AtlasSession')
