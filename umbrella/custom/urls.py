from django.urls import path

from . import views

app_name = "custom"


urlpatterns = [
    path("", views.custom_page, name='custom'),
]
