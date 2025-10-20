from django.contrib import admin

from .models import Path, PathType, StaticPath

# Register your models here.
admin.site.register(Path)
admin.site.register(PathType)
admin.site.register(StaticPath)
