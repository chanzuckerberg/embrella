from django.urls import path
from . import views
from django.shortcuts import render

app_name = "custom"


urlpatterns = [
    path("", views.custom_page, name='custom'),
    path("umbrella/user_guide/", views.user_guide_view, name="user_guide"),
]