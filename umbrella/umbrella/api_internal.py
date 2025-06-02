import json
from math import ceil
import os
import os.path
import random
import socket
import traceback
import uuid
from datetime import datetime, timezone
from urllib.parse import urljoin

import paramiko
import requests
from bs4 import BeautifulSoup
from cryo_grids.models import CryoGrid
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import BooleanField, Case, Count, F, Q, Value, When
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from processes.models import (
    Annotation,
    Pipe,
    PipeInPlan,
    PipeJoint,
    ProcPlan,
    ProcRun,
    Review,
    ReviewTomogram,
    Tomograms,
)
from processes.utils import SortMetadataModel
from processes.views import get_base_url
from projects.models import Project
from rapidfuzz import fuzz, process
from tem.models import MsiSession, Project

HOST = "10.50.120.90"
PORT = 22
USERNAME = os.getenv('REMOTE_ID')
PASSWORD = os.getenv('REMOTE_PASSWORD')
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')


def get_grids_by_user(request):
    user_id = request.GET.get('user_id')

    # Annotate each grid with an is_default flag based on the grid name.
    queryset = CryoGrid.objects.select_related('intended_project', 'user').annotate(
        project_name=F('intended_project__name'),
        username=F('user__username'),
        is_default=Case(
            When(name__icontains="default grid", then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    )

    if user_id:
        queryset = queryset.filter(user_id=user_id)

    # Order by create_on in descending order (newest first)get_tomoget_tomo
    queryset = queryset.order_by('-create_on')

    # Return the data including the computed is_default field
    grids = queryset.values('id', 'name', 'project_name', 'username', 'is_default', 'create_on')
    return JsonResponse(list(grids), safe=False)

def get_available_grids(request):
    project_id = request.GET.get('project_id')

    if project_id:
        # Ensure project_id is valid
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Project not found."}, status=404)

        # Get the available grids for the given project
        available_grids = CryoGrid.objects.filter(
            trashed=False,
            msisession__project=project
        ).select_related('grid_box').distinct()

        # Format the data
        grids_data = []
        for grid in available_grids:
            grids_data.append({
                "grid_id": grid.id,
                "grid_name": grid.name,
                "grid_box_id": grid.grid_box.id,
                "grid_box_name": grid.grid_box.name,
            })

        return JsonResponse(grids_data, safe=False)
    else:
        return JsonResponse({"error": "Project ID not provided."}, status=400)

def get_grids_by_cassette(request):
    cassette_id = request.GET.get('cassette_id')
    if cassette_id:
        grids = CryoGrid.objects.filter(grid_cassette__id=cassette_id)
        # Format the data
        print(grids)
        grids_data = []
        for grid in grids:
            grids_data.append({
                "grid_id": grid.id,
                "grid_user": grid.user.username,
                "grid_name": grid.name,
                "grid_specimen": grid.specimen.__str__(),
                "grid_slot_number": grid.slot_number_in_cassette,
                "grid_project_name": grid.intended_project.name,
            })

        return JsonResponse(grids_data, safe=False)
    else:
        return JsonResponse({"error": "Cassette ID not provided."}, status=400)

def _get_data_by_msi_session_data_type(plan, session, data_types=[]):
        # Find the first pipe in the plan
        valid_pipes_in_plan = PipeInPlan.objects.filter(plan=plan, step=1).distinct()
        if len(valid_pipes_in_plan) > 1:
            raise ValueError("Plan can only have one first pipe.")
        # Get the available tomogram for the given session and plan input pipe
        valid_pipes = []
        for vpp in valid_pipes_in_plan:
            my_pipe = vpp.pipe
            # filter data_types as the right input_pipe
            input_joints = PipeJoint.objects.filter(pipe_in_plan__pipe=my_pipe,input_pathtype__static_path__data_type__in=data_types)
            if not input_joints:
                continue
            # there should always be only one
            valid_pipes.append(input_joints[0].input_pipe_in_plan.pipe)
        return valid_pipes

def get_tomo_by_msi_session(request):
    """
    Return form selector options as json response of Tomograms
    that belong to the session and are valid as the input of the first pipe in the plan.
    """
    plan_id = request.GET.get('plan_id')
    session_id = request.GET.get('session_id')
    run_number = request.GET.get('run_number')
    if not plan_id:
        return JsonResponse({"error": "Processing Plan ID not provided."}, status=400)
    else:
        # Ensure session_id is valid
        try:
            plan = ProcPlan.objects.get(id=plan_id)
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "Processing Plan not found."}, status=404)
    if not session_id:
        return JsonResponse({"error": "MsiSession ID not provided."}, status=400)
    else:
        # Ensure session_id is valid
        try:
            session = MsiSession.objects.get(id=session_id)
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "MsiSession not found."}, status=404)
    # tomo
    try:
        valid_pipes = _get_data_by_msi_session_data_type(plan, session, data_types=['rec','deno'])
    except Exception as e:
        return JsonResponse({"error": e }, status=404)

    input_tomos = []
    for valid_pipe in valid_pipes:
        tomo = Tomograms.objects.filter(
            msi_session=session, pipe_data__pipe=valid_pipe
        )
        if run_number and run_number.strip():  # Check if run_number exists and is not empty
            tomo = tomo.filter(pipe_data__run__name=run_number)
        tomo = tomo.distinct()
        input_tomos.extend(list(tomo))
    tomo_data = []
    for tomo in input_tomos:
        tomo_data.append({
            "id": tomo.id,
            "name": tomo.pipe_data.__str__(),
        })

    try:
        valid_pipes = _get_data_by_msi_session_data_type(plan, session, data_types=['pick'])
    except Exception as e:
        return JsonResponse({"error": e }, status=404)
    if not valid_pipes:
        return JsonResponse([tomo_data, []], safe=False)
    input_picks = []
    for valid_pipe in valid_pipes:
        pick = Annotation.objects.filter(
            msi_session=session, pipe_data__pipe=valid_pipe, annotation_type='point'
        )
        if run_number and run_number.strip():  # Check if run_number exists and is not empty
            pick = pick.filter(pipe_data__run__name=run_number)
        pick = pick.distinct()
        input_picks.extend(list(pick))
    pick_data = []
    for pick in input_picks:
        pick_data.append({
            "id": pick.id,
            "name": pick.pipe_data.__str__(),
        })

    return JsonResponse([tomo_data, pick_data], safe=False)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewView(View):
    def get(self, request, review_id=None):
        """
        Handle GET requests for both endpoints:
        - /api/reviews/ (list all reviews with pagination, sorting, and search)
        - /api/reviews/{review_id}/ (get specific review metadata)

        Query Parameters:
        - limit (number, default=20): Max number of reviews to return
        - offset (number, default=0): For pagination
        - orderBy (string, default=updatedAt:desc): Sort order
        - search (string, default=""): Fuzzy matches on reviewName and sessionId
        """
        if review_id:
            return self.get_review_metadata(request, review_id)
        
        search = ''
        sort_field = 'updatedAt'
        sort_order = 'desc'
        limit = None
        offset = 0

        requested_page = 1

        try:
            for item in json.loads(request.GET.get('q', default="[]")):
                match item['category']:
                    case 'search':
                        search = item['value']
                    case 'sort':
                        sort_field = item['value'][0]
                    case 'asc':
                        sort_order = 'asc' if item['value'][0] else 'desc'
                    case 'page':
                        limit = 20
                        requested_page = item['value'][0]
                        offset = (requested_page - 1) * limit

            # Map frontend sort fields to database fields
            sort_field_map = {
                'requestedAt': 'created_at',
                'updatedAt': 'updated_at',
                'reviewName': 'review_name',
                'sessionId': 'msi_session__name',
                'status': 'status'
            }

            # Start with base queryset
            queryset = Review.objects.select_related('msi_session', 'requestor').all()

            # Apply search filter
            if search:
                # Get all reviews first
                all_reviews = list(queryset)

                # Preprocess search term
                search = search.lower().replace('-', '').replace(' ', '')

                # Filter reviews based on similarity threshold
                SIMILARITY_THRESHOLD = 70
                filtered_reviews = []

                for review in all_reviews:
                    if (fuzz.ratio(search, review.review_name) >= SIMILARITY_THRESHOLD or 
                        fuzz.ratio(search, review.requestor.username) >= SIMILARITY_THRESHOLD or
                        fuzz.ratio(search, review.msi_session.name) >= SIMILARITY_THRESHOLD or
                        fuzz.ratio(search, review.reconstruction_type) >= SIMILARITY_THRESHOLD or
                        search in review.review_name.lower() or
                        search in review.requestor.username.lower() or
                        search in review.msi_session.name.lower() or
                        search in review.reconstruction_type.lower()):
                        filtered_reviews.append(review)

                # Update queryset with filtered reviews
                queryset = Review.objects.filter(
                    review_id__in=[r.review_id for r in filtered_reviews]
                ).select_related('msi_session', 'requestor')

            # Apply sorting
            db_sort_field = sort_field_map.get(sort_field, 'created_at')
            if sort_order == 'desc':
                queryset = queryset.order_by(f'-{db_sort_field}')
            else:
                queryset = queryset.order_by(db_sort_field)

            # Get total count before pagination
            total_count = queryset.count()

            if limit is None:
                limit = total_count

            # Apply pagination
            queryset = queryset[offset:offset + limit]

            # Format the response
            reviews_data = []
            for review in queryset:
                # Determine status based on reviewed count
                if review.reviewed_count == 0:
                    status = "Not Started"
                elif review.reviewed_count < review.total_count:
                    status = "In Progress"
                else:
                    status = "Complete"

                reviews_data.append({
                    "review": {
                        "id": str(review.review_id),
                        "name": review.review_name,
                        "type": review.review_type,
                        "url": f"{get_base_url()}/admin/processes/review/{review.review_id}",
                        "annotationObjects": review.objects_of_interest.split(',') 
                            if review.objects_of_interest is not None else []
                    },
                    "session": {
                        "id": review.msi_session.pk,
                        "name": review.msi_session.name,
                        "url": f"{get_base_url()}/admin/tem/msisession/{review.msi_session.pk}",
                    },
                    "runId": review.run_id,
                    "reconstructionType": review.reconstruction_type,
                    "updatedAt": review.updated_at.isoformat(),
                    "status": status,
                    "reviewedCount": review.reviewed_count,
                    "totalCount": review.total_count,
                    "reviewer": {
                        "id": str(review.requestor.id) if review.requestor else None,
                        "name": review.requestor.username if review.requestor else None
                    }
                })

            return JsonResponse({
                "result": reviews_data,
                "pagination": {
                    "page": requested_page,
                    "pageSize": limit,
                    "totalPages": ceil(total_count / limit),
                    "totalResults": total_count
                },
                "sortBy": SortMetadataModel(
                    sort='updatedAt' if sort_field is not None else None,
                    asc=sort_order is 'asc'
                ).model_dump()
            }, safe=False)

        except Exception as e:
            print(f"Error in get reviews: {str(e)}")  # Add logging
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)

    def get_review_metadata(self, request, review_id):
        """
        Get detailed metadata for a specific review.

        Args:
            request: HTTP request
            review_id: UUID of the review

        Returns:
            JSON object with review metadata:
            {
                "reviewId": UUID,
                "reviewName": string,
                "owner": {
                    "id": UUID,
                    "name": string
                },
                "tomograms": [
                    {
                        "tomogramId": string,
                        "status": "pending" | "accepted" | "rejected" | "uncertain"
                    }
                ]
            }
        """
        try:
            # Convert string to UUID if needed
            if isinstance(review_id, str):
                try:
                    review_id = uuid.UUID(review_id)
                except ValueError:
                    return JsonResponse({"error": "Invalid review ID format"}, status=400)

            # Get the review with related data
            review = Review.objects.select_related('requestor').get(review_id=review_id)

            # Get all tomograms for this review
            tomograms = ReviewTomogram.objects.filter(review=review).values('tomogram_id', 'quality', 'position_id')

            # Format the response
            response_data = {
                "reviewId": str(review.review_id),
                "reviewName": review.review_name,
                "owner": {
                    "id": str(review.requestor.id) if review.requestor else None,
                    "name": review.requestor.username if review.requestor else None
                },
                "availableAnnotationObjects": review.objects_of_interest.split(',') 
                    if review.objects_of_interest is not None else [],
                "tomograms": [
                    {
                        "tomogramId": tomo['tomogram_id'],
                        "status": tomo['quality'] if tomo['quality'] else 'pending',
                        "position": tomo['position_id'] if tomo['position_id'] else "None"
                    }
                    for tomo in tomograms
                ]
            }

            return JsonResponse(response_data)

        except Review.DoesNotExist:
            return JsonResponse({"error": "Review not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, review_id=None):
        """
        Handle POST requests for both review creation and saving review results.

        If review_id is provided, check the URL path to determine the action:
        - /save/ -> save review results
        - /complete/ -> mark review as completed
        Otherwise, create a new review.
        """
        if review_id:
            # Check the URL path to determine the action
            if 'save' in request.path:
                return self.save_review(request, review_id)
            elif 'complete' in request.path:
                return self.complete_review(request, review_id)
            else:
                return JsonResponse({"error": "Invalid endpoint"}, status=400)

        # Original review creation logic
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Validate required fields
        required_fields = ['reviewName', 'reviewType', 'sessionId', 'runId', 'reconstructionType', 'requestor']
        for field in required_fields:
            if field not in data:
                return JsonResponse({"error": f"Missing required field: {field}"}, status=400)

        # Validate reconstruction type
        valid_reconstruction_types = ['DCTF', 'Denoised', 'SART']
        if data['reconstructionType'] not in valid_reconstruction_types:
            return JsonResponse({"error": f"Invalid reconstruction type. Must be one of: {', '.join(valid_reconstruction_types)}"}, status=400)

        try:
            # Get the session
            session = MsiSession.objects.get(id=data['sessionId'])
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)

        try:
            # Get the requestor user
            requestor = User.objects.get(id=data['requestor'])
        except User.DoesNotExist:
            return JsonResponse({"error": "Requestor user not found"}, status=404)

        # Check for duplicate review name
        if Review.objects.filter(review_name=data['reviewName']).exists():
            return JsonResponse({
                "error": "Duplicate review name",
                "details": f"A review with name '{data['reviewName']}' already exists"
            }, status=400)

        # Check if there are tomograms to review
        tomogram_count = ReviewTomogram.objects.filter(
            session=session,
            run_id=data['runId'],
            reconstruction_type=data['reconstructionType']
        ).count()

        if tomogram_count == 0:
            return JsonResponse({
                "error": "No tomograms found for review",
                "details": f"No tomograms found for session {session.name}, run {data['runId']}, and reconstruction type {data['reconstructionType']}"
            }, status=400)

        # Create the review
        try:
            review = Review.objects.create(
                review_name=data['reviewName'],
                review_type=data['reviewType'],
                run_id=data['runId'],
                reconstruction_type=data['reconstructionType'],
                msi_session=session,
                requestor=requestor,
                status='not_started',
                total_count=tomogram_count,  # Set total count to actual tomogram count
                reviewed_count=0,
                objects_of_interest=data['annotationObjects']
            )

            # Update ReviewTomogram records to associate them with this review
            ReviewTomogram.objects.filter(
                session=session,
                run_id=data['runId'],
                reconstruction_type=data['reconstructionType']
            ).update(review=review)

            # Return the created review
            return JsonResponse({
                "reviewId": str(review.review_id),
                "sessionId": review.msi_session.name,
                "runId": review.run_id,
                "reconstructionType": review.reconstruction_type,
                "reviewName": review.review_name,
                "totalCount": review.total_count,
                "status": "not_started",
                "createdAt": review.created_at.isoformat()
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def save_review(self, request, review_id):
        """
        Save review results for multiple tomograms.
        """
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
                print(f"Received data: {data}")  # Debug log
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            # Validate required fields
            required_fields = ['reviewId', 'savePath', 'annotations']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({"error": f"Missing required field: {field}"}, status=400)

            # Get the review
            try:
                review = Review.objects.get(review_id=review_id)
                print(f"Found review: {review.review_id}")  # Debug log
            except Review.DoesNotExist:
                print(f"Review not found with ID: {review_id}")  # Debug log
                return JsonResponse({"error": "Review not found"}, status=404)

            # Validate quality values
            valid_qualities = ['accepted', 'rejected', 'uncertain']

            # Validate annotations
            for annotation in data['annotations']:
                if 'tomogramId' not in annotation or 'quality' not in annotation:
                    return JsonResponse({"error": "Each annotation must have tomogramId and quality"}, status=400)
                if annotation['quality'] not in valid_qualities:
                    return JsonResponse({"error": f"Invalid quality value. Must be one of: {', '.join(valid_qualities)}"}, status=400)
                if annotation['quality'] == 'rejected' and not annotation.get('rejectionReasons'):
                    return JsonResponse({"error": "Rejection reasons are required when quality is rejected"}, status=400)

            # Update tomogram reviews
            for annotation in data['annotations']:
                try:
                    tomogram = ReviewTomogram.objects.get(
                        review=review,
                        tomogram_id=annotation['tomogramId']
                    )
                    print(f"Updating tomogram: {tomogram.tomogram_id}")  # Debug log

                    # Update tomogram review data
                    tomogram.quality = annotation['quality']

                    # Handle rejection reasons
                    if annotation['quality'] == 'rejected':
                        tomogram.rejection_reasons = json.dumps(annotation['rejectionReasons'])
                    else:
                        tomogram.rejection_reasons = json.dumps([])  # Empty array instead of None

                    # Handle object labels
                    if 'objectLabels' in annotation:
                        tomogram.object_labels = json.dumps(annotation['objectLabels'])
                    else:
                        tomogram.object_labels = json.dumps([])  # Empty array instead of None

                    tomogram.save()

                except ReviewTomogram.DoesNotExist:
                    print(f"Tomogram not found: {annotation['tomogramId']}")  # Debug log
                    return JsonResponse({"error": f"Tomogram not found: {annotation['tomogramId']}"}, status=404)

            # Calculate counts
            total_count = ReviewTomogram.objects.filter(review=review).count()
            reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__in=['accepted', 'rejected', 'uncertain']
            ).count()

            # Update review's save path and reviewed count
            review.save_path = data['savePath']
            review.reviewed_count = reviewed_count
            review.save()

            # Return success response with counts
            return JsonResponse({
                "ok": True,
                "savedAt": datetime.now(timezone.utc).isoformat(),
                "savePath": data['savePath'],
                "reviewedCount": reviewed_count,
                "totalCount": total_count
            })

        except Exception as e:
            print(f"Unexpected error in save_review: {str(e)}")  # Debug log
            import traceback
            print(traceback.format_exc())  # Print full traceback
            return JsonResponse({"error": str(e)}, status=500)

    def complete_review(self, request, review_id):
        """
        Mark a review as completed.

        Args:
            request: HTTP request
            review_id: UUID of the review

        Request Body:
        {
            "reviewId": UUID
        }

        Returns:
        {
            "ok": true,
            "finishedAt": string (ISO timestamp),
            "savePath": string
        }
        """
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            # Validate review ID matches URL parameter
            if data.get('reviewId') != review_id:
                return JsonResponse({"error": "Review ID in request body does not match URL parameter"}, status=400)

            # Convert string to UUID if needed
            try:
                review_id = uuid.UUID(review_id)
            except ValueError:
                return JsonResponse({"error": "Invalid review ID format"}, status=400)

            # Get the review
            try:
                review = Review.objects.get(review_id=review_id)
            except Review.DoesNotExist:
                return JsonResponse({"error": "Review not found"}, status=404)

            # Update review status
            review.status = 'completed'
            review.save()

            # Update review counts
            review = tomogram.review
            review.reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__in=['accepted', 'rejected', 'uncertain', 'exemplary']
            ).count()
            review.save()

            # Return success response
            return JsonResponse({
                "ok": True,
                "finishedAt": datetime.utcnow().isoformat() + 'Z',
                "savePath": review.save_path if review.save_path else None
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

def export_review_results(request, review_id):
    """
    Export final review annotations after completion.

    Args:
        request: HTTP request
        review_id: UUID of the review to export

    Returns:
        JSON file containing the review annotations
    """
    try:
        # Convert string to UUID if needed
        if isinstance(review_id, str):
            try:
                review_id = uuid.UUID(review_id)
            except ValueError:
                return JsonResponse({"error": "Invalid review ID format"}, status=400)

        # Get the review with related tomograms
        review = Review.objects.get(review_id=review_id)

        # Check if review is completed
        if review.status != 'completed':
            return JsonResponse({"error": "Review must be completed before exporting"}, status=400)

        # Get all tomograms for this review
        tomograms = ReviewTomogram.objects.filter(review=review)

        # Format the export data
        export_data = {
            "reviewId": str(review.review_id),
            "reviewName": review.review_name,
            "sessionId": review.msi_session.name,
            "runId": review.run_id,
            "reconstructionType": review.reconstruction_type,
            "completedAt": review.updated_at.isoformat(),
            "annotations": []
        }

        # Add tomogram annotations
        for tomogram in tomograms:
            annotation = {
                "tomogramId": tomogram.tomogram_id,
                "quality": tomogram.quality if tomogram.quality else "pending",
                "rejectionReasons": [],
                "objectLabels": []
            }

            # Add rejection reasons if quality is rejected
            if tomogram.quality == "rejected" and tomogram.rejection_reasons:
                try:
                    annotation["rejectionReasons"] = json.loads(tomogram.rejection_reasons)
                except json.JSONDecodeError:
                    # Fallback for old format (comma-separated)
                    annotation["rejectionReasons"] = tomogram.rejection_reasons.split(",")

            # Add object labels if they exist
            if tomogram.object_labels:
                try:
                    annotation["objectLabels"] = json.loads(tomogram.object_labels)
                except json.JSONDecodeError:
                    # Fallback for old format (comma-separated)
                    annotation["objectLabels"] = tomogram.object_labels.split(",")

            export_data["annotations"].append(annotation)

        # Create the response with the JSON data
        response = JsonResponse(export_data)

        # Set headers for file download
        filename = f"review_{review_id}_export.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Type'] = 'application/json'
        response['Content-Length'] = len(json.dumps(export_data))

        return response

    except Review.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_review_tomograms(request, review_id):
    """
    Get all tomograms for a specific review.

    Args:
        request: HTTP request
        review_id: String ID of the review

    Returns:
        JSON array of tomograms with their status
        [
            { "tomogramId": "tomo_001", "status": "pending" },
            { "tomogramId": "tomo_002", "status": "rejected" }
        ]
    """
    print(f"Getting tomograms for review_id: {review_id}")
    print(f"Type of review_id: {type(review_id)}")

    try:
        # First check if the review exists
        try:
            # Try to convert to UUID if it's a valid UUID string
            try:
                review_uuid = uuid.UUID(review_id)
                review = Review.objects.get(review_id=review_uuid)
            except ValueError:
                # If not a valid UUID, try to find by string ID
                review = Review.objects.get(review_id=review_id)

            print(f"Found review: {review.review_id}")
        except Review.DoesNotExist:
            print(f"Review not found with ID: {review_id}")
            # List all available review IDs for debugging
            all_reviews = Review.objects.all()
            print("Available review IDs:")
            for r in all_reviews:
                print(f"- {r.review_id} (Name: {r.review_name})")
            return JsonResponse({"error": "Review not found"}, status=404)

        # Get tomograms for the review
        tomograms = ReviewTomogram.objects.filter(
            review=review
        ).values('tomogram_id', 'quality')

        print(f"Found {tomograms.count()} tomograms")

        # Format the response
        tomograms_data = [
            {
                "tomogramId": tomo['tomogram_id'],
                "status": tomo['quality'] if tomo['quality'] else 'pending'
            }
            for tomo in tomograms
        ]

        return JsonResponse(tomograms_data, safe=False)

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ReviewTomogramView(View):
    def get(self, request, review_id, tomogram_id):
        """
        Get detailed information about a specific tomogram in a review.

        Args:
            request: HTTP request
            review_id: String ID of the review
            tomogram_id: ID of the tomogram

        Returns:
            JSON object with tomogram details:
            {
                "tomogramId": string,
                "displayName": string,
                "zarrPath": string,
                "existingReview": {
                    "quality": "accepted" | "rejected" | "uncertain",
                    "rejectionReasons": string[],
                    "objectLabels": string[]
                }
            }
        """
        print(f"Getting tomogram details for review_id: {review_id}, tomogram_id: {tomogram_id}")

        try:
            # First check if the review exists
            try:
                review = Review.objects.get(review_id=review_id)
                print(f"Found review: {review.review_id}")
            except Review.DoesNotExist:
                print(f"Review not found with ID: {review_id}")
                return JsonResponse({"error": "Review not found"}, status=404)

            # Get the specific tomogram
            try:
                tomogram = ReviewTomogram.objects.get(
                    review__review_id=review_id,
                    tomogram_id=tomogram_id
                )
                print(f"Found tomogram: {tomogram.tomogram_id}")
            except ReviewTomogram.DoesNotExist:
                print(f"Tomogram not found with ID: {tomogram_id}")
                return JsonResponse({"error": "Tomogram not found"}, status=404)

            # Format the response
            response_data = {
                "tomogramId": tomogram.tomogram_id,
                "displayName": f"{tomogram.position_id}",
                "zarrPath": None,
                "existingReview": {
                    "quality": None,
                    "rejectionReasons": [],
                    "objectLabels": []
                }
            }

            # Construct zarr path based on reconstruction type
            if review.reconstruction_type.lower() == "sart":
                vol_suffix = "vol003"
                job_name = "aretomo3"
            elif review.reconstruction_type.lower() == "dctf":
                vol_suffix = "vol001"
                job_name = "aretomo3"
            else:
                vol_suffix = ""  # denoised
                job_name = "denoise"

            # Original zarr path construction (commented out for now)
            response_data["zarrPath"] = f"https://czii-onsite.czbiohub.org/krios1.processing/{job_name}/{review.msi_session.name}/{review.run_id}/{vol_suffix}/{tomogram.position_id}_Vol.zarr"

            response_data["contrastLimits"] = [-0.00001, 0.00001]  # Default contrast limits

            # Add review details if they exist
            if tomogram.quality:
                response_data["existingReview"]["quality"] = tomogram.quality

                # Add rejection reasons if quality is rejected
                if tomogram.quality == "rejected" and tomogram.rejection_reasons:
                    try:
                        response_data["existingReview"]["rejectionReasons"] = json.loads(tomogram.rejection_reasons)
                    except json.JSONDecodeError:
                        # Fallback for old format (comma-separated)
                        response_data["existingReview"]["rejectionReasons"] = tomogram.rejection_reasons.split(",")

                # Add object labels if they exist
                if tomogram.object_labels:
                    try:
                        response_data["existingReview"]["objectLabels"] = json.loads(tomogram.object_labels)
                    except json.JSONDecodeError:
                        # Fallback for old format (comma-separated)
                        response_data["existingReview"]["objectLabels"] = tomogram.object_labels.split(",")

            return JsonResponse(response_data)

        except Exception as e:
            print(f"Unexpected error in GET: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, review_id, tomogram_id):
        """
        Submit a review result for a specific tomogram.

        Args:
            request: HTTP request
            review_id: String ID of the review
            tomogram_id: ID of the tomogram

        Request Body:
        {
            "tomogramId": string,
            "quality": "accepted" | "rejected" | "uncertain",
            "rejectionReasons": string[],    // only if rejected
            "objectLabels": string[]         // optional
        }

        Returns:
        { "ok": true }
        """
        print(f"Submitting review result for review_id: {review_id}, tomogram_id: {tomogram_id}")

        try:
            # Parse request body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            # Validate required fields
            if 'quality' not in data:
                return JsonResponse({"error": "Missing required field: quality"}, status=400)

            # Validate quality value
            valid_qualities = ['accepted', 'rejected', 'uncertain', 'exemplary', 'pending']
            if data['quality'] not in valid_qualities:
                return JsonResponse({"error": f"Invalid quality value. Must be one of: {', '.join(valid_qualities)}"}, status=400)

            # Get the tomogram
            try:
                tomogram = ReviewTomogram.objects.get(
                    review__review_id=review_id,
                    tomogram_id=tomogram_id
                )
                print(f"Found tomogram: {tomogram.tomogram_id}")
            except ReviewTomogram.DoesNotExist:
                print(f"Tomogram not found with ID: {tomogram_id}")
                return JsonResponse({"error": "Tomogram not found"}, status=404)

            # Update tomogram review data
            tomogram.quality = data['quality']

            # Handle rejection reasons - store as JSON string
            if data['quality'] == 'rejected':
                tomogram.rejection_reasons = json.dumps(data['rejectionReasons'])
            else:
                tomogram.rejection_reasons = json.dumps([])

            # Handle object labels - store as JSON string
            if 'objectLabels' in data:
                tomogram.object_labels = json.dumps(data['objectLabels'])

            # Save the changes
            tomogram.save()

            # Update review counts
            review = tomogram.review
            review.reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__in=['accepted', 'rejected', 'uncertain', 'exemplary']
            ).count()
            review.save()

            return JsonResponse({"ok": True})

        except Exception as e:
            print(f"Unexpected error in POST: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class SessionView(View):
    """View to handle both /api/sessions and /api/sessions/{session_id} endpoints"""

    def get_session_data(self, session):
        """Get runs data for a session"""
        runs_data = []
        seen_runs = set()  # Track unique combinations of runId and reconstructionType

        # Get all ProcRuns for this session
        proc_runs = session.procrun_set.all()

        for proc_run in proc_runs:
            # Get tomogram count directly from ReviewTomogram table
            review_data = ReviewTomogram.objects.filter(
                run_id=proc_run.name,
                session=session
            ).values('reconstruction_type').annotate(
                tomogram_count=Count('tomogram_id', distinct=True)
            )

            # Create a dictionary to store tomogram counts by reconstruction type
            tomogram_counts = {data['reconstruction_type']: data['tomogram_count'] for data in review_data}

            # Check all three possibilities for each run
            reconstruction_types = [
                {
                    'type': 'DCTF',
                    'job_name': 'aretomo3',
                    'vol_number': 'vol001'
                },
                {
                    'type': 'SART',
                    'job_name': 'aretomo3',
                    'vol_number': 'vol003'
                },
                {
                    'type': 'Denoised',
                    'job_name': 'denoise',
                    'vol_number': 'vol001'
                }
            ]

            for recon_info in reconstruction_types:
                recon_type = recon_info['type']
                job_name = recon_info['job_name']
                vol_number = recon_info['vol_number']

                # Create a unique key for this run and reconstruction type combination
                run_key = f"{proc_run.name}_{recon_type}"

                # Only add if we haven't seen this combination before
                if run_key not in seen_runs:
                    seen_runs.add(run_key)

                    # Construct save path
                    save_path = f"/hpc/group.czii/krios1.processing/project/{job_name}/{session.name}/{proc_run.name}/{vol_number}"

                    # Get tomogram count for this reconstruction type, default to 0 if not found
                    tomogram_count = tomogram_counts.get(recon_type, 0)

                    runs_data.append({
                        "runId": proc_run.name,
                        "numTomograms": tomogram_count,
                        "reconstructionType": recon_type,
                        "savePath": save_path
                    })

        return {
            "sessionId": session.id,  # Use session name as ID
            "sessionName": session.name,
            "createdAt": session.created_at.isoformat() if session.created_at else None,
            "projectName": session.project.name if session.project else None,
            "runs": runs_data
        }

    def get(self, request, session_id=None):
        """
        Handle GET requests for both endpoints:
        - /api/sessions/ (list all sessions)
        - /api/sessions/{session_id} (get specific session)
        """
        try:
            if session_id:
                # Get specific session
                try:
                    session = MsiSession.objects.select_related('project').get(name=session_id)
                except MsiSession.DoesNotExist:
                    return JsonResponse({"error": "Session not found"}, status=404)

                session_data = self.get_session_data(session)
                return JsonResponse(session_data, safe=False)

            else:
                # List all sessions
                search = request.GET.get('search', '').strip()

                # Start with base queryset
                sessions_qs = MsiSession.objects.select_related(
                    'project'
                ).prefetch_related(
                    'procrun_set'
                )

                # Apply search filter if provided
                if search:
                    sessions_qs = sessions_qs.filter(
                        Q(name__icontains=search) |
                        Q(project__name__icontains=search)
                    )

                # Get all sessions
                sessions = sessions_qs.order_by('-created_at')

                # Get data for each session
                sessions_data = []
                for session in sessions:
                    session_data = self.get_session_data(session)
                    # Include session if it has any runs (regardless of tomogram count)
                    if session_data["runs"]:
                        sessions_data.append(session_data)

                return JsonResponse(sessions_data, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

