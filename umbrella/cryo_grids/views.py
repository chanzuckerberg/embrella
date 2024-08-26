from django.shortcuts import render
from cryo_grids.models import CryoGrid, CryoGridBox, CryoGridCassette, Puck, CryoGridCassette, \
    PlungeFreezingSession, PlungeFreezingPlan

from django.views.decorators.http import require_http_methods

from django.db.models import F, Q, Count
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.timezone import now
from datetime import timedelta
from .utils import CryoGridsQueryParams
from pydantic import ValidationError
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
@require_http_methods(["GET"])
def get_all_grid_boxes(request):
    if request.GET.get('valid', 'true') != 'true':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    try:
        # Get all unique names of grid boxes
        unique_grid_boxes = CryoGridBox.objects.order_by('name').values('name').distinct()
        # Extract names into a list
        unique_names = [box['name'] for box in unique_grid_boxes]

        return JsonResponse({"unique_names": unique_names}, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def grid_boxes_view(request):
    # Assuming you have a way to get `data.id`, perhaps from a query parameter or some logic.
    data_id = request.GET.get('id')  # Example way to get data.id, adjust as needed.

    context = {
        'title': 'Gridboxes',
        'data': {
            'id': data_id
        }
    }
    return render(request, 'cryo_grids/detail.html', context)


from django.http import JsonResponse
from .models import CryoGrid, CryoGridBox


def get_specific_grids(request):
    grid_box_name = request.GET.get('grid_box_name')
    username = request.GET.get('username')

    try:
        # Initialize the query set
        specific_grids = CryoGrid.objects.all()

        # Filter by grid box name if provided
        if grid_box_name:
            try:
                grid_box = CryoGridBox.objects.get(name=grid_box_name)
                specific_grids = specific_grids.filter(grid_box=grid_box)
            except CryoGridBox.DoesNotExist:
                return JsonResponse({"error": "Grid box not found."}, status=404)

        # Filter by username if provided
        if username:
            specific_grids = specific_grids.filter(user__username=username)

        # Join with the User and CryoGridCassette tables and select relevant fields
        specific_grids = specific_grids.select_related('grid_box', 'user', 'grid_cassette').values(
            'id', 'create_on', 'name', 'notes', 'position_in_box', 'grid_box_id',
            'clipped', 'trashed', 'slot_number_in_cassette', 'grid_cassette_id',
            'user__username', 'grid_cassette__name'
        )

        # Format the data
        grids_data = list(specific_grids)

        return JsonResponse(grids_data, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




@require_http_methods(["GET"])
def available_filters(request):
    try:
        # Base queryset with annotations for counting occurrences
        queryset = CryoGrid.objects.select_related(
            'intended_project', 'freezing_session', 'grid_box__puck', 'user',
            'grid_cassette', 'freezing_plan'
        ).prefetch_related(
            'msisession', 'freezing_plan__sample', 'freezing_plan__tags',
            'atlassession__group'
        )

        # Calculate the date ranges based on UTC time
        current_time = now()
        date_ranges = {
            'last_1_month': current_time - timedelta(days=30),
            'last_3_months': current_time - timedelta(days=90),
            'last_6_months': current_time - timedelta(days=180),
        }

        # Aggregating counts for each filter
        filters = {
            'project': list(queryset.annotate(project_temp_name=F('intended_project__name'))
                        .values(project_temp_name=F('project_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('project_temp_name')
                        .values(name=F('project_temp_name'), count=F('count'))),
            'puck': list(queryset.annotate(puck_temp_name=F('grid_box__puck__name'))
                        .values(puck_temp_name=F('puck_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('puck_temp_name')
                        .values(name=F('puck_temp_name'), count=F('count'))),
            'sample': list(queryset.annotate(sample_temp_name=F('freezing_plan__sample__name'))
                        .values(sample_temp_name=F('sample_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('sample_temp_name')
                        .values(name=F('sample_temp_name'), count=F('count'))),
            'user': list(queryset.annotate(user_temp_name=F('user__username'))
                        .values(user_temp_name=F('user_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('user_temp_name')
                        .values(name=F('user_temp_name'), count=F('count'))),
            'cassette': list(queryset.annotate(cassette_temp_name=F('grid_cassette__name'))
                        .values(cassette_temp_name=F('cassette_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('cassette_temp_name')
                        .values(name=F('cassette_temp_name'), count=F('count'))),
            'screenSession': list(queryset.annotate(screen_session_temp_name=F('atlassession__group__name'))
                        .values(screen_session_temp_name=F('screen_session_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('screen_session_temp_name')
                        .values(name=F('screen_session_temp_name'), count=F('count'))),
            'msiSession': list(queryset.annotate(msi_session_temp_name=F('msisession__name'))
                        .values(msi_session_temp_name=F('msi_session_temp_name'))
                        .annotate(count=Count('id'))
                        .order_by('msi_session_temp_name')
                        .values(name=F('msi_session_temp_name'), count=F('count'))),
            'status': list(queryset.values(is_trashed=F('trashed'))
                        .annotate(count=Count('id'))
                        .order_by('trashed')),
            'date': [
                {"range": "last_1_month", "count": queryset.filter(create_on__gte=date_ranges['last_1_month']).count()},
                {"range": "last_3_months", "count": queryset.filter(create_on__gte=date_ranges['last_3_months']).count()},
                {"range": "last_6_months", "count": queryset.filter(create_on__gte=date_ranges['last_6_months']).count()}
            ]
        }

        # Process the 'sample' filter and replace sample_name with the detailed information
        processed_samples = []
        for item in filters['sample']:
            if 'sample_temp_name' in item:
                # Get the associated freezing plans based on the sample name
                freezing_plans = PlungeFreezingPlan.objects.filter(sample__name=item['sample_temp_name'])

                # Create a string that summarizes the freezing plan details
                freezing_plan_details = []
                for freezing_plan in freezing_plans:
                    tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
                    plan_str = f"{item['sample_temp_name']} with {tag_names}" if tag_names else f"{item['sample_temp_name']} without tag"
                    freezing_plan_details.append(plan_str)

                # Replace sample_temp_name with the concatenated string
                item['sample_temp_name'] = ' | '.join(freezing_plan_details)

            processed_samples.append(item)

        filters['sample'] = processed_samples

        # Convert to the expected output format
        response_data = {
            "filters": filters
        }

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_cryo_grids_details(request):
    try:
        # Parse and validate query parameters using Pydantic
        query_params = CryoGridsQueryParams(**request.GET.dict())

        # Retrieve filter type
        filter_type = query_params.filter_type

        # Process user_name to handle firstname.lastname format
        if query_params.user_name:
            query_params.user_name = [
                username.split('@')[0] for username in query_params.user_name
            ]

        # Base queryset
        queryset = CryoGrid.objects.select_related(
            'intended_project', 'freezing_session', 'grid_box__puck', 'user',
            'grid_cassette', 'freezing_plan'
        ).prefetch_related(
            'msisession', 'freezing_plan__sample', 'freezing_plan__tags',
            'atlassession__group'
        ).values(
            'id',
            grid_name=F('name'),
            cassette_name=F('grid_cassette__name'),
            project_name=F('intended_project__name'),
            project_id=F('intended_project__id'),
            puck=F('grid_box__puck__name'),
            userID=F('user__id'),
            username=F('user__username'),
            status=F('trashed'),
            created_on=F('create_on'),
            msisession_id=F('msisession__id'),
            msisession_name=F('msisession__name'),
            fz_session_id=F('freezing_session__id'),
            fz_session_datetime=F('freezing_session__datetime'),
            fz_plan_id=F('freezing_plan__id'),
            screening_session_name=F('atlassession__group__name'),
            fz_plan_sample_id=F('freezing_plan__sample__id')
        ).order_by('-created_on')

        filter_mappings = {
            'project_name': 'intended_project__name__in',
            'cassette_name': 'grid_cassette__name__in',
            'grid_name': 'name__in',
            'puck_name': 'grid_box__puck__name__in',
            'user_name': 'user__username__in',
            'msi_session_name': 'msisession__name__in',
            'screen_session_name': 'atlassession__group__name__in',
        }

        if filter_type == 'AND':
            # Apply all filters as an intersection of conditions
            filters = Q()
            for key, filter_field in filter_mappings.items():
                values = getattr(query_params, key)
                if values:
                    filters &= Q(**{filter_field: values})
            queryset = queryset.filter(filters)
        elif filter_type == 'OR':
            # Apply each filter separately and get the intersection of the results
            initial_queryset = CryoGrid.objects.none()
            for key, filter_field in filter_mappings.items():
                values = getattr(query_params, key)
                if values:
                    filtered_queryset = queryset.filter(Q(**{filter_field: values}))
                    initial_queryset = initial_queryset | filtered_queryset

            # Only keep grids that appear in all filtered querysets
            queryset = initial_queryset.distinct()

        if not queryset.exists():
            return JsonResponse({'Result': []}, status=200)

        formatted_result = {}
        for item in queryset:
            grid_id = item['id']

            # Format datetime field if it exists
            fz_session_datetime_formatted = (
                item['fz_session_datetime'].strftime("%Y-%m-%d %H:%M")
                if item['fz_session_datetime'] else None
            )

            # Fetching freezing plan sample and tag details
            freezing_plan_list = []
            try:
                freezing_plan = PlungeFreezingPlan.objects.get(id=item['fz_plan_id'])
                for sample in freezing_plan.sample.all():
                    sample_id = sample.id
                    sample_name = sample.name
                    tag_names = ', '.join(freezing_plan.tags.values_list('name', flat=True))
                    sample_url = f"http://umbrella.czbiohub.org/admin/samples/{sample_id}"
                    plan_str = {
                        'id': sample_id,
                        'name': f"{sample_name} with {tag_names}" if tag_names else f"{sample_name} without tag",
                        'url': sample_url
                    }
                    freezing_plan_list.append(plan_str)
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Related freezing plan not found.'}, status=404)
            except ValidationError as e:
                return JsonResponse({'error': f'Validation error: {str(e)}'}, status=422)

            if grid_id not in formatted_result:
                grid_url = f"http://umbrella.czbiohub.org/admin/cryo_grids/cryogrid/{grid_id}"
                project_url = f"http://umbrella.czbiohub.org/admin/projects/project/{item['project_id']}"
                formatted_result[grid_id] = {
                    'grid': {
                        'id': grid_id,
                        'name': f"{item['grid_name']} (id={grid_id})",
                        'trashed': item['status'],
                        'url': grid_url,
                        'createdAt': item['created_on'],
                    },
                    'cassette': {
                        'name': item['cassette_name'],
                    },
                    'project': {
                        'id': item['project_id'],
                        'name': item['project_name'],
                        'url': project_url
                    },
                    'puck': {
                        'name': item['puck']
                    },
                    'user': {
                        'id': item['userID'],
                        'name': item['username']
                    },
                    'freezingPlan': {
                        'id': item['fz_plan_id'],
                        'sample': freezing_plan_list,
                    },
                    'freezingSession': {
                        'id': item['fz_session_id'],
                        'createdAt': fz_session_datetime_formatted
                    },
                    'screeningSession': item['screening_session_name'],
                    'msiSession': [],
                }

            # Append MSI session details
            if item['msisession_id']:
                msi_url = f"http://umbrella.czbiohub.org/tem/{item['msisession_id']}"
                formatted_result[grid_id]['msiSession'].append({
                    'id': item['msisession_id'],
                    'name': item['msisession_name'],
                    'url': msi_url
                })

        # Filter results by sample name if provided
        if query_params.sample_name:
            matching_results = {}
            sample_name_input = query_params.sample_name

            for grid_id, data in formatted_result.items():
                sample_list = data['freezingPlan']['sample']

                # Filter samples within each freezing plan that match any sample_name in the list
                matching_samples = [
                    sample for sample in sample_list
                    if any(s_name in sample['name'] for s_name in sample_name_input)
                ]

                if matching_samples:
                    data['freezingPlan']['sample'] = matching_samples
                    matching_results[grid_id] = data

            formatted_result = matching_results

        formatted_result_list = list(formatted_result.values())

        return JsonResponse({'Result': formatted_result_list})

    except ValidationError as e:
        return JsonResponse({'error': e.errors()}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)