from django.contrib import admin
from .models import Microscope, Camera, ImagingWorkflow, Software, SessionPlan, MsiSession
from .models import ScreenSessionGroup, AtlasSession
from .models import Magnification, CalibratedPixelSize

# Register your models here.
admin.site.register(Microscope)
admin.site.register(Camera)
admin.site.register(Magnification)
admin.site.register(CalibratedPixelSize)
admin.site.register(ImagingWorkflow)
admin.site.register(Software)
admin.site.register(SessionPlan)
admin.site.register(MsiSession)
admin.site.register(ScreenSessionGroup)
admin.site.register(AtlasSession)
