from django.urls import path

from . import views

#register app namespace
app_name = "tem"

urlpatterns = [
    path("reserve", views.reserve_session, name="reserve"),
    path("create", views.create_session, name="create"),
    path("<int:session_id>/", views.detail, name="detail"),
    path("scrn/", views.reserve_scrn_session_group, name="scrnreserve"),
    path("scrn/create", views.create_scrn_session_group, name="scrncreate"),
    path("scrn/<int:scrn_group_id>/", views.scrn_group_detail, name="scrndetail"),
    path("session_list/", views.get_all_sessions, name="get"),
    path("path_list/", views.get_all_image_paths, name="path")
]
