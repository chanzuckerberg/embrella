from django.urls import path

from .views import token_scopes, token_self

urlpatterns = [
    path("self", token_self, name="token-self"),
    path("scopes", token_scopes, name="token-scopes"),
]
