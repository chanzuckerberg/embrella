from django.contrib import admin
from .models import Microscope, Camera, ImagingWorkflow, Software, SessionPlan, Session
from .models import ScreenSessionGroup, ScreenSession

# Register your models here.
admin.site.register(Microscope)
admin.site.register(Camera)
admin.site.register(ImagingWorkflow)
admin.site.register(Software)
admin.site.register(SessionPlan)
admin.site.register(Session)
admin.site.register(ScreenSessionGroup)
admin.site.register(ScreenSession)
