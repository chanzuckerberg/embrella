from django.urls import path

from . import views

#register app namespace
app_name = "projects"

urlpatterns = [
    path("", views.index, name="index"),
]
