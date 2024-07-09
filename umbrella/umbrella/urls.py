"""
URL configuration for umbrella project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from umbrella.ping import ping
from cryo_grids.views import get_grids_by_user, get_available_grids
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
import google


urlpatterns = [
    path('', RedirectView.as_view(url='/umbrella/', permanent=True)),
    path('admin/', admin.site.urls, name='admin'),
    path(
        "google_sso/", include("django_google_sso.urls", namespace="django_google_sso")
    ),
    path('umbrella/', include('custom.urls'),name='umbrella'),
    path('projects/', include('projects.urls')),
    path('tem/', include('tem.urls')),
    path('processes/', include('processes.urls')),
    path('ping/', ping),
    path('admin/login/', auth_views.LoginView.as_view(), name='login'),
    path('admin/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('grids_by_user/', get_grids_by_user, name='get_grids_by_user'),
    path('get_available_grids', get_available_grids, name='get_available_grids'),
]


# change header name
admin.site.site_header = 'Embrella'
admin.site.site_title = 'Embrella'

