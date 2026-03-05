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


@admin.register(MsiSession)
class MsiSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "project", "session_plan", "magnification", "created_at")
    list_filter = ("session_plan", "magnification")
    raw_id_fields = ("grid", "frames", "mdocs", "sums", "parents", "atlas", "atlas_session")


admin.site.register(ScreenSessionGroup)
admin.site.register(AtlasSession)
