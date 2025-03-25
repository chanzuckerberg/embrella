from django.urls import path

from . import views

#register app namespace
app_name = "tem"

urlpatterns = [
    path("reserve", views.reserve_session, name="reserve"),
    path("create", views.create_session, name="create"),
    path("create_msi_name", views.create_msi_name, name="create_msi_name"),
    path("validate_msi_name", views.validate_msi_name, name="validate_msi_name"),
    path("<int:session_id>/", views.detail, name="detail"),
    path("scrn/", views.reserve_scrn_session_group, name="scrnreserve"),
    path("scrn/create", views.create_scrn_session_group, name="scrncreate"),
    path("scrn/<int:scrn_group_id>/", views.scrn_group_detail, name="scrndetail"),
    path("session_list/", views.get_all_sessions, name="get"),
    path("path_list/", views.get_all_image_paths, name="path"),
    path("scrn_filter/", views.get_all_scrns, name="get all scrn sessions"),
    path('detail/', views.render_screening_form, name='render_screening_form'),
    path("specific_scrn/", views.get_specific_session, name='specific_scrn'),
    path('get_projects/', views.get_projects, name='get_projects'),
]
