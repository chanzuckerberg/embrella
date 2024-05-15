from django.urls import path

from . import views

#register app namespace
app_name = "processes"

urlpatterns = [
    path("", views.reserve_run, name="reserve"),
    path("create", views.create_run, name="create"),
    path("<int:run_id>/", views.detail, name="detail"),
    #path("run_list/", views.get_all_sessions, name="get"),
    #path("path_list/", views.get_all_image_paths, name="path")
]
