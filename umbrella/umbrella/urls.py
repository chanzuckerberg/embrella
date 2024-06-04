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
from umbrella.ping import ping, custom_admin_redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth.views import LoginView
from django.contrib.auth import views as auth_views

from django.shortcuts import redirect
from django.urls import reverse


urlpatterns = [
    path('', RedirectView.as_view(url='/umbrella/', permanent=True)),
    path('umbrella/', admin.site.urls, name='umbrella'),
    path('custom_page/', include('custom.urls'),name='custom_page'),
    path('projects/', include('projects.urls')),
    path('tem/', include('tem.urls')),
    path('processes/', include('processes.urls')),
    path('ping/', ping),
    path('umbrella/login/', auth_views.LoginView.as_view(), name='login'),
    path('umbrella/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]


# change header name
admin.site.site_header = 'Lab auto workflow'
admin.site.site_title = 'Lab auto workflow'

