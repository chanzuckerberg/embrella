from django.http import JsonResponse

def ping(request):
    return JsonResponse({'message': 'pong'})