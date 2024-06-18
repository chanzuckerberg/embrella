from django.http import JsonResponse
from cryo_grids.models import CryoGrid
def get_grids_by_user(request):
    user_id = request.GET.get('user_id')

    if user_id:
        grids = CryoGrid.objects.filter(user_id=user_id).values('id', 'name')
    else:
        grids = CryoGrid.objects.values('id', 'name')

    return JsonResponse(list(grids), safe=False)