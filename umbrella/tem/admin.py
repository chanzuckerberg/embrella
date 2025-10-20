from django.contrib import admin

from .models import (
    AtlasSession,
    CalibratedPixelSize,
    Camera,
    ImagingWorkflow,
    Magnification,
    Microscope,
    MsiSession,
    ScreenSessionGroup,
    SessionPlan,
    Software,
)

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
