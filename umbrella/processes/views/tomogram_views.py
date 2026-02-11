"""
Tomogram-related view functions for processing workflows.

This module contains views for syncing, listing, and managing tomogram data.
"""
import io
import json
import logging
import os
from contextlib import redirect_stdout
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from pydantic import ValidationError
from rest_framework.decorators import api_view
from tem.models import MsiSession

from common import clusterio
from processes.models import ProcRun, Review, ReviewTomogram
from processes.validation import (
    GridModel,
    MSISessionModel,
    ProcPlanModel,
    ProcRunModel,
    ProjectModel,
    ResponseModel,
    SortMetadataModel,
    TomogramModel,
    UnprocessableEntity,
    UserModel,
    tomoQueryParams,
)

from .constants import get_base_url

logger = logging.getLogger(__name__)


@extend_schema(
    methods=["GET"],
    description="Returns a paginated list of tomogram-related metadata and filters using 'q' param.",
    parameters=[
        OpenApiParameter(name='q', required=False, type=OpenApiTypes.STR),
        OpenApiParameter(name='page', required=False, type=int),
        OpenApiParameter(name='pageSize', required=False, type=int),
    ],
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@require_http_methods(["GET"])
def get_tomo_details(request):
    try:
        # Parse 'q' parameter if provided
        raw_q_param = request.GET.get('q', None)
        if raw_q_param:
            try:
                q_param = json.loads(raw_q_param)
            except json.JSONDecodeError as e:
                return JsonResponse({'error': f'Invalid JSON format for q parameter: {str(e)}'}, status=400)
        else:
            q_param = []

        query_data = request.GET.dict()
        query_data['q'] = q_param

        # Validate query parameters
        try:
            query_params = tomoQueryParams(**query_data)
        except ValidationError as e:
            raise UnprocessableEntity(detail=f"Validation error: {str(e)}")

        # Pagination and sorting defaults
        page = int(request.GET.get('page', 1))  # Default to first page
        page_size = int(request.GET.get('pageSize', 10))  # Default page size is 10
        sort_field = 'updated_at'
        asc = False

        # Helper function to extract values
        def extract_value(value):
            return value[0] if isinstance(value, list) and value else value

        # Override pagination and sorting if provided in q_param
        for item in q_param:
            if item['category'] == 'sort':
                sort_value = extract_value(item['value'])
                if sort_value == 'updatedAt':
                    sort_field = 'updated_at'
            elif item['category'] == 'asc':
                asc_value = extract_value(item['value'])
                asc = bool(asc_value) if isinstance(asc_value, bool) else asc_value.lower() == 'true'
            elif item['category'] == 'page':
                page = int(extract_value(item['value']))
            elif item['category'] == 'pageSize':
                page_size = int(extract_value(item['value']))

        # Determine sort order
        sort_order = sort_field if asc else f'-{sort_field}'

        # Base queryset with selected related fields
        queryset = ProcRun.objects.select_related(
            'proc_plan',
            'msi_session',
            'freezing_session',
            'msi_session__project',
            'msi_session__grid',
            'msi_session__user',
            'msi_session__atlas_session',
            'msi_session__atlas_session__group',
            'msi_session__grid__specimen',
        ).prefetch_related(
            'msi_session__grid__specimen__samples',  # Updated prefetch: use many-to-many field "samples"
        ).filter(
            proc_plan__name__in=['czii-live', 'czii-denoise'],
        ).values(
            'id',
            'name',
            'notes',
            'created_at',
            'updated_at',
            'proc_plan_id',
            'msi_session_id',
            proc_plan_plan_id=F('proc_plan__id'),
            proc_plan_name=F('proc_plan__name'),
            msi_session_name=F('msi_session__name'),
            msi_session_notes=F('msi_session__notes'),
            msi_session_project_id=F('msi_session__project_id'),
            msi_session_grid_id=F('msi_session__grid_id'),
            cryogrid_id=F('msi_session__grid__id'),
            cryogrid_name=F('msi_session__grid__name'),
            cryogrid_trashed=F('msi_session__grid__trashed'),
            cryogrid_created_at=F('msi_session__grid__updated_on'),
            project_id=F('msi_session__project__id'),
            project_name=F('msi_session__project__name'),
            user_id=F('msi_session__user__id'),
            user_name=F('msi_session__user__username'),
            specimen_id=F('msi_session__grid__specimen__id'),
            screening_session_name=F('msi_session__atlas_session__group__name'),
        ).order_by(sort_order)

        date_mapping = {
            'last_1_month': 1,
            'last_3_months': 3,
            'last_6_months': 6,
        }

        filter_criteria = Q()

        for item in q_param:
            category = item['category']
            values = item['value']

            if category == 'procPlan':
                filter_criteria &= Q(proc_plan__name__in=values)
            elif category == 'user':
                user_filter = Q()
                for value in values:
                    user_filter |= Q(msi_session__user__username__startswith=value)
                filter_criteria &= user_filter
            elif category == 'screeningSession':
                session_filter = Q()
                for value in values:
                    if value is None:
                        session_filter |= Q(msi_session__atlas_session__group__name__isnull=True)
                    else:
                        session_filter |= Q(msi_session__atlas_session__group__name__icontains=value)
                filter_criteria &= session_filter
            elif category == 'grid':
                filter_criteria &= Q(msi_session__grid__name__in=values)
            elif category == 'project':
                filter_criteria &= Q(msi_session__project__name__in=values)
            elif category == 'msiSession':
                session_name_filter = Q()
                for value in values:
                    if value is None:
                        session_name_filter |= Q(msi_session__name__isnull=True)
                    else:
                        session_name_filter |= Q(msi_session__name__icontains=value)
                filter_criteria &= session_name_filter
            elif category == 'tomograms':
                filter_criteria &= Q(name__in=values)
            elif category == 'date' and values:
                date_value = values[0] if isinstance(values, list) else values
                if date_value in date_mapping:
                    months = date_mapping[date_value]
                    now_dt = datetime.now()
                    start_date = now_dt - timedelta(days=months * 30)
                    filter_criteria &= Q(updated_at__gte=start_date)
                else:
                    return JsonResponse({'error': f'Invalid value for date filter: {date_value}'}, status=400)
            elif category == 'sample':
                # Updated sample filtering using the many-to-many field "samples"
                sample_filter = Q()
                for value in values:
                    if value is None:
                        sample_filter |= Q(msi_session__grid__specimen__samples__isnull=True)
                    elif "with " in value:
                        parts = value.split(" with ")
                        sample_name = parts[0].strip()
                        ontology_value = parts[1].strip() if len(parts) > 1 else None
                        sample_filter |= Q(
                            msi_session__grid__specimen__samples__name=sample_name,
                            msi_session__grid__specimen__samples__ontology__icontains=ontology_value,
                        )
                    elif "without tag" in value:
                        sample_name = value.replace(" without tag", "").strip()
                        sample_filter |= Q(
                            msi_session__grid__specimen__samples__name=sample_name,
                        ) & (Q(msi_session__grid__specimen__samples__ontology='') | Q(msi_session__grid__specimen__samples__ontology__isnull=True))
                    else:
                        sample_filter |= Q(msi_session__grid__specimen__samples__name=value)
                filter_criteria &= sample_filter

        queryset = queryset.filter(filter_criteria)

        # Prepare unique results for the response
        unique_results = {}
        base_url = get_base_url()
        for entry in queryset:
            procrun_id = entry.get('id')
            if procrun_id not in unique_results:
                proc_run_updated_at = datetime.fromisoformat(str(entry.get('updated_at'))).strftime('%Y-%m-%d') if entry.get('updated_at') else None
                cryogrid_created_at = datetime.fromisoformat(str(entry.get('cryogrid_created_at'))).strftime('%Y-%m-%d') if entry.get('cryogrid_created_at') else None
                run_name = entry.get('name')
                session_name = entry.get('msi_session_name')
                response_model = ResponseModel(
                    tomograms=TomogramModel(
                        id=procrun_id,
                        name=run_name,
                        url=f"{base_url}/admin/processes/procrun/{procrun_id}",
                    ),
                    procPlan=ProcPlanModel(
                        id=entry.get('proc_plan_plan_id'),
                        name=entry.get('proc_plan_name'),
                        url=f"{base_url}/admin/processes/procplan/{entry.get('proc_plan_plan_id')}",
                    ),
                    procRun=ProcRunModel(
                        id=procrun_id,
                        notes=entry.get('notes'),
                        updatedAt=str(proc_run_updated_at),
                    ),
                    grid=GridModel(
                        id=entry.get('cryogrid_id'),
                        name="{} (id={})".format(entry.get('cryogrid_name'), entry.get('cryogrid_id')),
                        trashed=entry.get('cryogrid_trashed'),
                        url=f"{base_url}/admin/cryo_grids/cryogrid/{entry.get('cryogrid_id')}",
                        createdAt=str(cryogrid_created_at),
                    ),
                    project=ProjectModel(
                        id=entry.get('project_id'),
                        name=entry.get('project_name'),
                        url=f"{base_url}/admin/projects/project/{entry.get('project_id')}",
                    ),
                    user=UserModel(
                        id=entry.get('user_id'),
                        name=entry.get('user_name').split('@')[0] if '@' in entry.get('user_name') else entry.get('user_name'),
                    ),
                    msiSession=MSISessionModel(
                        id=entry.get('msi_session_id'),
                        name=session_name,
                        url=f"{base_url}/admin/tem/msisession/{entry.get('msi_session_id')}",
                    ),
                )
                result = response_model.model_dump()
                if session_name and run_name:
                    result['metadata_url'] = f"{base_url}/metadata/view/{session_name}/{run_name}"
                else:
                    result['metadata_url'] = None
                unique_results[procrun_id] = result

        response_data = list(unique_results.values())

        # Paginate the formatted response data using Django's Paginator
        paginator = Paginator(response_data, page_size)
        try:
            paginated_data = paginator.page(page)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)

        result = {
            'result': list(paginated_data),
            'pagination': {
                'page': paginated_data.number,
                'pageSize': int(page_size),
                'totalPages': paginator.num_pages,
                'totalResults': paginator.count,
            },
            'sortBy': SortMetadataModel(
                sort='updatedAt' if sort_field is not None else None,
                asc=asc,
            ).model_dump(),
        }

        return JsonResponse(result, safe=False)
    except UnprocessableEntity as e:
        return JsonResponse({'error': e.detail}, status=e.status_code)
    except Exception as e:
        logger.error(f'An unexpected error occurred: {str(e)}')
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def sync_tomograms_view(request):
    """View for the tomogram sync page"""
    try:
        # Get all sessions directly from MsiSession
        sessions = MsiSession.objects.all().order_by('-created_at')

        # Format sessions for template
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                "sessionId": str(session.id),
                "sessionName": session.name,
                "createdAt": session.created_at.isoformat() if session.created_at else None,
            })

        print(f"Found {len(sessions_data)} sessions")  # Debug print

        return render(request, 'customs/sync_tomograms.html', {
            'sessions': sessions_data,
            'error': None,
        })
    except Exception as e:
        logger.error(f"Error in sync_tomograms_view: {str(e)}")
        return render(request, 'customs/sync_tomograms.html', {
            'sessions': [],
            'error': f"Error loading sessions: {str(e)}",
        })


@require_http_methods(["GET"])
def get_runs(request):
    """API endpoint to get runs for a session"""
    session_id = request.GET.get('session')
    try:
        session = MsiSession.objects.get(id=session_id)
        # Get unique run IDs from ProcRun table for this session
        runs = ProcRun.objects.filter(msi_session=session).values('name').distinct()
        runs_data = [{'runId': run['name']} for run in runs]
        return JsonResponse({'runs': runs_data})
    except MsiSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


@require_http_methods(["GET"])
def get_tomogram_stats(request):
    """API endpoint to get tomogram statistics"""
    session_id = request.GET.get('session')
    run_id = request.GET.get('run')
    recon_type = request.GET.get('type', '').lower()

    print(f"Getting tomogram stats for - session_id: {session_id}, run_id: {run_id}, recon_type: {recon_type}")

    try:
        # Get zarr files for the selected configuration
        session = MsiSession.objects.get(id=session_id)
        print(f"Found session: {session.name}")

        # Construct path based on reconstruction type
        from processes.syncers import check_zarr_exists
        recon_type_lower = recon_type.lower()
        if recon_type_lower == 'sart':
            vol_dir = 'vol003'
            base_path = '/hpc/projects/krios1.processing/aretomo3'
        elif recon_type_lower == 'dctf':
            vol_dir = 'vol001'
            base_path = '/hpc/projects/krios1.processing/aretomo3'
        else:  # denoised
            vol_dir = ''
            base_path = '/hpc/projects/krios1.processing/denoise'

        session_path = f"{base_path}/{session.name}/{run_id}"
        full_path = f"{session_path}/{vol_dir}" if vol_dir else session_path

        # Use existing check_zarr_exists function from syncers
        zarr_files = check_zarr_exists(full_path)
        print(f"Found {len(zarr_files)} zarr files")

        # Simplified query directly on ReviewTomogram
        query = ReviewTomogram.objects.filter(
            session_id=session_id,
            run_id=run_id,
            reconstruction_type__iexact=recon_type,
        )

        print(f"Query: {query}")
        # Get the count from the database
        db_count = query.count()
        print(f"Found {db_count} tomograms in database")

        # Get some sample tomograms for debugging
        sample_tomograms = list(query.values('position_id', 'reconstruction_type', 'run_id')[:5])
        print(f"Sample tomograms: {sample_tomograms}")

        return JsonResponse({
            'db_count': db_count,  # Count from Embrella database
            'generated': len(zarr_files),  # Count from file server
            'zarr_files': zarr_files,  # Include the list of zarr files in the response
            'session_name': session.name,
            'run_id': run_id,
            'recon_type': recon_type,
        })
    except MsiSession.DoesNotExist:
        print(f"Session {session_id} not found")
        return JsonResponse({
            'error': 'Session not found',
        }, status=404)
    except Exception as e:
        print(f"Error in get_tomogram_stats: {str(e)}")
        return JsonResponse({
            'error': str(e),
        }, status=500)


@require_http_methods(["POST"])
async def start_sync(request):
    """API endpoint to start tomogram sync process"""
    session_id = request.POST.get('session')
    run_id = request.POST.get('run')
    recon_type = request.POST.get('reconType')

    print(f"Received parameters - session_id: {session_id}, run_id: {run_id}, recon_type: {recon_type}")

    if not all([session_id, run_id, recon_type]):
        return JsonResponse({
            'success': False,
            'message': 'Missing required parameters',
        }, status=400)

    try:
        # First check if session exists - using sync_to_async
        session = await sync_to_async(MsiSession.objects.get)(id=session_id)
        print(f"Found session: {session.name}")

        # Check for existing tomograms with the same parameters
        existing_tomograms = await sync_to_async(list)(ReviewTomogram.objects.filter(
            session=session,
            run_id=run_id,
            reconstruction_type__iexact=recon_type,
        ))

        if existing_tomograms:
            print(f"Found {len(existing_tomograms)} existing tomograms for this session/run/type combination")
            # Get list of existing position IDs
            existing_positions = {t.position_id for t in existing_tomograms}
            print(f"Existing positions: {existing_positions}")
        else:
            existing_positions = None

        # Try to find an existing review, but don't require it
        try:
            review = await sync_to_async(Review.objects.select_related('msi_session').get)(
                msi_session_id=session_id,
                run_id=run_id,
                reconstruction_type__iexact=recon_type,
            )
            print(f"Found existing review: {review}")
            review_id = review.review_id
        except Review.DoesNotExist:
            print(f"No existing review found for session {session_id}, run {run_id}, type {recon_type}")
            print("Will sync tomograms without associating them with a review")
            review_id = None

        # Import the sync functions
        from workflow.processors.aretomo3.syncer import AretomoSyncer
        from workflow.processors.denoiset.syncer import DenoiseSyncer

        # Capture stdout to get progress information
        output = io.StringIO()
        with redirect_stdout(output):
            # Use the appropriate sync function based on reconstruction type
            if recon_type.lower() in ['dctf', 'sart']:
                print(f"Starting AreTomo3 sync for session {session.name}, run {run_id}, type {recon_type}")
                syncer = AretomoSyncer(
                    base_path="/hpc/projects/krios1.processing/aretomo3",
                    log_dir=os.path.join(os.path.dirname(__file__), "logs"),
                )
                await sync_to_async(syncer.setup)(run_id=run_id, session_name=session.name)
                await sync_to_async(syncer.sync_results)()
            elif recon_type.lower() == 'denoised':
                print(f"Starting Denoise sync for session {session.name}, run {run_id}")
                syncer = DenoiseSyncer(
                    base_path="/hpc/projects/krios1.processing/denoise",
                    log_dir=os.path.join(os.path.dirname(__file__), "logs"),
                )
                await sync_to_async(syncer.setup)(run_id=run_id, session_name=session.name)
                await sync_to_async(syncer.sync_results)()
            else:
                raise ValueError(f"Unsupported reconstruction type: {recon_type}")

        # Get the captured output
        progress_output = output.getvalue()
        print("Sync process completed with output:", progress_output)

        # Update review total count if a review was found
        updated_total_count = None
        if review_id:
            try:
                review = await sync_to_async(Review.objects.get)(review_id=review_id)
                tomogram_count = await sync_to_async(
                    ReviewTomogram.objects.filter(
                        session=session,
                        run_id=run_id,
                        reconstruction_type__iexact=recon_type,
                    ).count
                )()

                old_count = review.total_count
                review.total_count = tomogram_count
                await sync_to_async(review.save)()
                updated_total_count = tomogram_count

                print(f"Updated review {review_id} total_count: {old_count} -> {tomogram_count}")
            except Exception as e:
                print(f"Error updating review total count: {e}")

        return JsonResponse({
            'success': True,
            'message': 'Sync process completed successfully',
            'progress': progress_output,
            'existing_tomograms': len(existing_tomograms) if existing_tomograms else 0,
            'review_associated': review_id is not None,
            'updated_total_count': updated_total_count,
        })
    except MsiSession.DoesNotExist:
        print(f"Session {session_id} not found in database")
        return JsonResponse({
            'success': False,
            'message': f'Session with ID {session_id} not found',
        }, status=404)
    except Exception as e:
        logger.error(f"Error in start_sync: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e),
        }, status=500)
