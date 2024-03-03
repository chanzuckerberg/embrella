from django.urls import path

from . import views

#register app namespace
app_name = "tem"

urlpatterns = [
    path("", views.reserve_session, name="reserve"),
    path("create", views.create_session, name="create"),
    path("<int:session_id>/", views.detail, name="detail"),
]
