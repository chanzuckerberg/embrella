"""Top-level URLconf for the cdpp pipeline registry (/cdpp/v1/)."""

from django.urls import path

from . import views

urlpatterns = [
    path("v1/pipelines/", views.list_cdpp_pipelines, name="cdpp_list_pipelines"),
]
