from django.contrib import admin

from .models import *
# Register your models here.
admin.site.register(MetaKey)
admin.site.register(Task)
admin.site.register(ProcSoftware)
admin.site.register(PipelinePlan)
admin.site.register(PlanPipe)
admin.site.register(GlobalParam)
admin.site.register(PipeParam)
admin.site.register(ProcRun)
admin.site.register(RunGlobalValue)
admin.site.register(RunPipeValue)
admin.site.register(RunPipeData)

