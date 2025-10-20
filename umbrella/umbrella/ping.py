from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view


@extend_schema(methods=["GET"], description="Ping endpoint that returns pong.")
@api_view(["GET"])
def ping(request):
    return JsonResponse({'message': 'pong'})



