from django.contrib import admin

from .models import Site, Dewar, Cane, Puck,CryoGridBox
from .models import PlungeFreezingDevice, PlungeFreezingSession, PlungeFreezingPlan, CryoGrid
from .models import Sample

admin.site.register(Site)
admin.site.register(Dewar)
admin.site.register(Cane)
admin.site.register(Puck)
admin.site.register(CryoGridBox)
admin.site.register(PlungeFreezingDevice)
admin.site.register(PlungeFreezingSession)
admin.site.register(PlungeFreezingPlan)
admin.site.register(CryoGrid)
admin.site.register(Sample)
