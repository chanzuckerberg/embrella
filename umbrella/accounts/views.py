from http import HTTPStatus

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import APIToken
from .scopes import grantable_scopes
from .tokens import describe

# Swagger section, instead of the default "api" from the path prefix
TAGS = ["tokens"]

TOKEN_IDENTITY = inline_serializer(
    name="TokenIdentity",
    fields={"id": serializers.IntegerField(), "username": serializers.CharField()},
)

TOKEN_SELF = inline_serializer(
    name="TokenSelf",
    fields={
        "user": TOKEN_IDENTITY,
        "bot": TOKEN_IDENTITY,
        "name": serializers.CharField(),
        "scopes": serializers.ListField(child=serializers.CharField()),
        "audience": serializers.CharField(),
        "expires_at": serializers.DateTimeField(allow_null=True),
    },
)

TOKEN_SCOPES = inline_serializer(
    name="TokenScopes", fields={"scopes": serializers.ListField(child=serializers.CharField())}
)


@extend_schema(
    summary="Who the presenting API token is",
    tags=TAGS,
    description="Token only. Used by MCP and other services that verify Embrella tokens.",
    responses={HTTPStatus.OK: TOKEN_SELF, HTTPStatus.UNAUTHORIZED: OpenApiResponse(description="No API token")},
)
@api_view(["GET"])
def token_self(request):
    # request.auth is the APIToken when TokenFromMiddleware authenticated the request
    if not isinstance(request.auth, APIToken):
        return Response({"error": "Requires an API token"}, status=HTTPStatus.UNAUTHORIZED)
    return Response(describe(request.auth))


@extend_schema(
    summary="Scopes grantable on API tokens",
    tags=TAGS,
    description="Embrella scopes plus extension scopes (TOKEN_EXTRA_SCOPES) checked only by other services.",
    responses={HTTPStatus.OK: TOKEN_SCOPES},
)
@api_view(["GET"])
def token_scopes(request):
    return Response({"scopes": grantable_scopes()})
