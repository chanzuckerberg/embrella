"""
API views for process and review management.

Contains API endpoints for:
- Tomogram queries by MSI session
- Review CRUD operations (list, create, get, save, complete)
- Review export functionality
- Tomogram review management
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from stores.models import Cluster, resolve_review_path
from tem.models import MsiSession
from umbrella.contrast_limits import compute_optimal_contrast_limits

from processes.models import (
    Annotation,
    PipeInPlan,
    PipeJoint,
    ProcPlan,
    Review,
    ReviewTomogram,
    Tomograms,
)
from processes.services.cluster_resolver import cluster_id_for_run
from processes.validation import SortMetadataModel

logger = logging.getLogger(__name__)


def _get_data_by_msi_session_data_type(plan, session, data_types=[]):
    """
    Helper function to get valid pipes for a given plan and session based on data types.

    Args:
        plan: ProcPlan instance
        session: MsiSession instance
        data_types: List of data type strings to filter by

    Returns:
        List of valid pipes
    """
    # Find the first pipe in the plan
    valid_pipes_in_plan = PipeInPlan.objects.filter(plan=plan, step=1).distinct()
    if len(valid_pipes_in_plan) > 1:
        raise ValueError("Plan can only have one first pipe.")
    # Get the available tomogram for the given session and plan input pipe
    valid_pipes = []
    for vpp in valid_pipes_in_plan:
        my_pipe = vpp.pipe
        # filter data_types as the right input_pipe
        input_joints = PipeJoint.objects.filter(
            pipe_in_plan__pipe=my_pipe, input_pathtype__data_kind__data_type__in=data_types
        )
        if not input_joints:
            continue
        # there should always be only one
        valid_pipes.append(input_joints[0].input_pipe_in_plan.pipe)
    return valid_pipes


@extend_schema(
    methods=["GET"],
    description="""
    Returns form selector options for Tomograms and Annotations belonging to an MSI session,
    that are valid as inputs of the first pipe in the specified processing plan.
    Returns a 2-element list:
    1. List of tomograms with `rec`/`deno` data types.
    2. List of annotation picks (`point` type) with `pick` data type.
    """,
    parameters=[
        OpenApiParameter(name="plan_id", required=True, type=str, description="Processing Plan ID"),
        OpenApiParameter(name="session_id", required=True, type=str, description="MSI Session ID"),
    ],
    responses={
        200: "List of tomograms and picks",
        400: "Missing required parameters",
        404: "Plan or Session not found, or data fetch error",
    },
)
@api_view(["GET"])
def get_tomo_by_msi_session(request):
    """
    Return form selector options as json response of Tomograms
    that belong to the session and are valid as the input of the first pipe in the plan.
    """
    plan_id = request.GET.get("plan_id")
    session_id = request.GET.get("session_id")
    run_number = request.GET.get("run_number")
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
        valid_pipes = _get_data_by_msi_session_data_type(plan, session, data_types=["rec", "deno"])
    except Exception as e:
        return JsonResponse({"error": e}, status=404)

    input_tomos = []
    for valid_pipe in valid_pipes:
        tomo = Tomograms.objects.filter(
            msi_session=session,
            pipe_data__pipe=valid_pipe,
        )
        if run_number and run_number.strip():  # Check if run_number exists and is not empty
            tomo = tomo.filter(pipe_data__run__name=run_number)
        tomo = tomo.distinct()
        input_tomos.extend(list(tomo))
    tomo_data = []
    for tomo in input_tomos:
        tomo_data.append(
            {
                "id": tomo.id,
                "name": tomo.pipe_data.__str__(),
            }
        )

    try:
        valid_pipes = _get_data_by_msi_session_data_type(plan, session, data_types=["pick"])
    except Exception as e:
        return JsonResponse({"error": e}, status=404)
    if not valid_pipes:
        return JsonResponse([tomo_data, []], safe=False)
    input_picks = []
    for valid_pipe in valid_pipes:
        pick = Annotation.objects.filter(
            msi_session=session,
            pipe_data__pipe=valid_pipe,
            annotation_type="point",
        )
        if run_number and run_number.strip():  # Check if run_number exists and is not empty
            pick = pick.filter(pipe_data__run__name=run_number)
        pick = pick.distinct()
        input_picks.extend(list(pick))
    pick_data = []
    for pick in input_picks:
        pick_data.append(
            {
                "id": pick.id,
                "name": pick.pipe_data.__str__(),
            }
        )

    return JsonResponse([tomo_data, pick_data], safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class ReviewView(View):
    """
    View for managing reviews - handles list, create, get, save, and complete operations.
    """

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

        search = ""
        sort_field = "updatedAt"
        sort_order = "desc"
        limit = None
        requested_page = 1

        try:
            for item in json.loads(request.GET.get("q", default="[]")):
                match item["category"]:
                    case "search":
                        search = item["value"]
                    case "sort":
                        sort_field = item["value"][0]
                    case "asc":
                        sort_order = "asc" if item["value"][0] else "desc"
                    case "page":
                        limit = 20
                        requested_page = item["value"][0]

            # Map frontend sort fields to database fields
            sort_field_map = {
                "requestedAt": "created_at",
                "updatedAt": "updated_at",
                "reviewName": "review_name",
                "sessionId": "msi_session__name",
                "status": "status",
            }

            # Start with base queryset
            queryset = Review.objects.select_related("msi_session", "requestor").all()

            # Apply search filter
            # TODO: Convert ReviewView into a DRF ViewSet with a proper filter
            #  backend instead of this hand-rolled search/sort/pagination logic.
            if search:
                search = search.strip()
                queryset = queryset.filter(
                    Q(review_name__icontains=search)
                    | Q(requestor__username__icontains=search)
                    | Q(msi_session__name__icontains=search)
                    | Q(reconstruction_type__icontains=search)
                )

            # Apply sorting
            db_sort_field = sort_field_map.get(sort_field, "created_at")
            if sort_order == "desc":
                queryset = queryset.order_by(f"-{db_sort_field}")
            else:
                queryset = queryset.order_by(db_sort_field)

            # Apply pagination
            from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

            if limit is None:
                limit = queryset.count()

            paginator = Paginator(queryset, limit, orphans=3)
            try:
                page_obj = paginator.page(requested_page)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            # Format the response
            reviews_data = []
            for review in page_obj:
                # Determine status based on reviewed count
                if review.reviewed_count == 0:
                    status = "Not Started"
                elif review.reviewed_count < review.total_count:
                    status = "In Progress"
                else:
                    status = "Complete"

                reviews_data.append(
                    {
                        "review": {
                            "id": str(review.review_id),
                            "name": review.review_name,
                            "type": review.review_type,
                            "url": f"/admin/processes/review/{review.review_id}",
                            "annotationObjects": review.objects_of_interest.split(",")
                            if review.objects_of_interest is not None
                            else [],
                        },
                        "session": {
                            "id": review.msi_session.pk,
                            "name": review.msi_session.name,
                            "url": f"/admin/tem/msisession/{review.msi_session.pk}",
                        },
                        "runId": review.run_id,
                        "reconstructionType": review.reconstruction_type,
                        "updatedAt": review.updated_at.isoformat(),
                        "status": status,
                        "reviewedCount": review.reviewed_count,
                        "totalCount": review.total_count,
                        "reviewer": {
                            "id": str(review.requestor.id) if review.requestor else None,
                            "name": review.requestor.username if review.requestor else None,
                        },
                    }
                )

            return JsonResponse(
                {
                    "result": reviews_data,
                    "pagination": {
                        "page": page_obj.number,
                        "pageSize": limit,
                        "totalPages": paginator.num_pages,
                        "totalResults": paginator.count,
                    },
                    "sortBy": SortMetadataModel(
                        sort="updatedAt" if sort_field is not None else None,
                        asc=sort_order == "asc",
                    ).model_dump(),
                },
                safe=False,
            )

        except Exception as e:
            logger.exception(f"Error in get reviews: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def get_review_metadata(self, request, review_id):
        """
        Get detailed metadata for a specific review.

        Args:
            request: HTTP request
            review_id: UUID of the review

        Returns:
            JSON object with review metadata including tomograms list
        """
        try:
            # Convert string to UUID if needed
            if isinstance(review_id, str):
                try:
                    review_id = uuid.UUID(review_id)
                except ValueError:
                    return JsonResponse({"error": "Invalid review ID format"}, status=400)

            # Get the review with related data
            review = Review.objects.select_related("requestor").get(review_id=review_id)

            # Get all tomograms for this review
            tomograms = ReviewTomogram.objects.filter(review=review).values("tomogram_id", "quality", "position_id")

            # Format the response and sort by position
            tomograms_list = [
                {
                    "tomogramId": tomo["tomogram_id"],
                    "status": tomo["quality"] if tomo["quality"] else "pending",
                    "position": tomo["position_id"] if tomo["position_id"] else "None",
                }
                for tomo in tomograms
            ]

            # Sort tomograms by position (handle compound position numbers like position_1_2, position_100_1)
            def extract_position_number(position_str):
                if position_str == "None":
                    return float("inf")  # Put "None" positions at the end
                try:
                    # Extract all numbers from "Position_X_Y" format
                    parts = position_str.split("_")
                    if len(parts) >= 2:
                        # Convert all numeric parts to integers for proper sorting
                        numbers = []
                        for part in parts[1:]:  # Skip "Position" part
                            try:
                                numbers.append(int(part))
                            except ValueError:
                                # If any part is not numeric, treat as invalid
                                return float("inf")
                        return numbers
                    else:
                        return float("inf")  # Invalid format
                except (ValueError, IndexError):
                    return float("inf")  # Put invalid positions at the end

            tomograms_list.sort(key=lambda x: extract_position_number(x["position"]))

            logger.debug(
                f"Sorted tomogram positions for review {review_id}: {[tomo['position'] for tomo in tomograms_list]}"
            )

            response_data = {
                "reviewId": str(review.review_id),
                "reviewName": review.review_name,
                "owner": {
                    "id": str(review.requestor.id) if review.requestor else None,
                    "name": review.requestor.username if review.requestor else None,
                },
                "availableAnnotationObjects": review.objects_of_interest.split(",")
                if review.objects_of_interest is not None
                else [],
                "tomograms": tomograms_list,
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
            if "save" in request.path:
                return self.save_review(request, review_id)
            elif "complete" in request.path:
                return self.complete_review(request, review_id)
            else:
                return JsonResponse({"error": "Invalid endpoint"}, status=400)

        # Original review creation logic
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Validate required fields
        required_fields = ["reviewName", "reviewType", "sessionId", "runId", "reconstructionType", "requestor"]
        for field in required_fields:
            if field not in data:
                return JsonResponse({"error": f"Missing required field: {field}"}, status=400)

        # Validate reconstruction type
        valid_reconstruction_types = ["DCTF", "Denoised", "SART"]
        if data["reconstructionType"] not in valid_reconstruction_types:
            return JsonResponse(
                {"error": f"Invalid reconstruction type. Must be one of: {', '.join(valid_reconstruction_types)}"},
                status=400,
            )

        try:
            # Get the session
            session = MsiSession.objects.get(id=data["sessionId"])
        except MsiSession.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)

        try:
            # Get the requestor user
            requestor = User.objects.get(id=data["requestor"])
        except User.DoesNotExist:
            return JsonResponse({"error": "Requestor user not found"}, status=404)

        # Check for duplicate review name
        if Review.objects.filter(review_name=data["reviewName"]).exists():
            return JsonResponse(
                {
                    "error": "Duplicate review name",
                    "details": f"A review with name '{data['reviewName']}' already exists",
                },
                status=400,
            )

        # Check if there are tomograms to review
        tomogram_count = ReviewTomogram.objects.filter(
            session=session,
            run_id=data["runId"],
            reconstruction_type=data["reconstructionType"],
        ).count()

        if tomogram_count == 0:
            return JsonResponse(
                {
                    "error": "No tomograms found for review",
                    "details": f"No tomograms found for session {session.name}, run {data['runId']}, and reconstruction type {data['reconstructionType']}",
                },
                status=400,
            )

        # Resolve the cluster this run executed on. `cluster` in the request body
        # takes precedence; otherwise infer from PipeExecution.parameters.
        resolved_cluster_id = data.get("cluster") or cluster_id_for_run(session.name, data["runId"])
        review_cluster = Cluster.objects.filter(cluster_id=resolved_cluster_id, is_active=True).first()

        # Create the review
        try:
            review = Review.objects.create(
                review_name=data["reviewName"],
                review_type=data["reviewType"],
                run_id=data["runId"],
                reconstruction_type=data["reconstructionType"],
                msi_session=session,
                requestor=requestor,
                cluster=review_cluster,
                status="not_started",
                total_count=tomogram_count,  # Set total count to actual tomogram count
                reviewed_count=0,
                objects_of_interest=data["annotationObjects"],
            )

            # Update ReviewTomogram records to associate them with this review
            ReviewTomogram.objects.filter(
                session=session,
                run_id=data["runId"],
                reconstruction_type=data["reconstructionType"],
            ).update(review=review)

            # Return the created review
            return JsonResponse(
                {
                    "reviewId": str(review.review_id),
                    "sessionId": review.msi_session.name,
                    "runId": review.run_id,
                    "reconstructionType": review.reconstruction_type,
                    "reviewName": review.review_name,
                    "totalCount": review.total_count,
                    "status": "not_started",
                    "createdAt": review.created_at.isoformat(),
                },
                status=201,
            )

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
                logger.debug(f"Received review save data for review {review_id}")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            # Validate required fields
            required_fields = ["reviewId", "savePath", "annotations"]
            for field in required_fields:
                if field not in data:
                    return JsonResponse({"error": f"Missing required field: {field}"}, status=400)

            # Get the review
            try:
                review = Review.objects.get(review_id=review_id)
                logger.debug(f"Found review: {review.review_id}")
            except Review.DoesNotExist:
                logger.warning(f"Review not found with ID: {review_id}")
                return JsonResponse({"error": "Review not found"}, status=404)

            # Validate quality values
            valid_qualities = ["accepted", "rejected", "uncertain"]

            # Validate annotations
            for annotation in data["annotations"]:
                if "tomogramId" not in annotation or "quality" not in annotation:
                    return JsonResponse({"error": "Each annotation must have tomogramId and quality"}, status=400)
                if annotation["quality"] not in valid_qualities:
                    return JsonResponse(
                        {"error": f"Invalid quality value. Must be one of: {', '.join(valid_qualities)}"}, status=400
                    )
                if annotation["quality"] == "rejected" and not annotation.get("rejectionReasons"):
                    return JsonResponse(
                        {"error": "Rejection reasons are required when quality is rejected"}, status=400
                    )

            # Update tomogram reviews
            for annotation in data["annotations"]:
                try:
                    tomogram = ReviewTomogram.objects.get(
                        review=review,
                        tomogram_id=annotation["tomogramId"],
                    )
                    logger.debug(f"Updating tomogram: {tomogram.tomogram_id}")

                    # Update tomogram review data
                    tomogram.quality = annotation["quality"]

                    # Handle rejection reasons
                    if annotation["quality"] == "rejected":
                        tomogram.rejection_reasons = json.dumps(annotation["rejectionReasons"])
                    else:
                        tomogram.rejection_reasons = json.dumps([])  # Empty array instead of None

                    # Handle object labels
                    if "objectLabels" in annotation:
                        tomogram.object_labels = json.dumps(annotation["objectLabels"])
                    else:
                        tomogram.object_labels = json.dumps([])  # Empty array instead of None

                    tomogram.save()

                except ReviewTomogram.DoesNotExist:
                    logger.warning(f"Tomogram not found: {annotation['tomogramId']}")
                    return JsonResponse({"error": f"Tomogram not found: {annotation['tomogramId']}"}, status=404)

            # Calculate counts
            total_count = ReviewTomogram.objects.filter(review=review).count()
            reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__in=["accepted", "rejected", "uncertain"],
            ).count()

            # Update review's save path and reviewed count
            review.save_path = data["savePath"]
            review.reviewed_count = reviewed_count
            review.save()

            # Return success response with counts
            return JsonResponse(
                {
                    "ok": True,
                    "savedAt": datetime.now(timezone.utc).isoformat(),
                    "savePath": data["savePath"],
                    "reviewedCount": reviewed_count,
                    "totalCount": total_count,
                }
            )

        except Exception as e:
            logger.exception(f"Unexpected error in save_review: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def complete_review(self, request, review_id):
        """
        Mark a review as completed.
        """
        try:
            # Parse request body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            # Validate review ID matches URL parameter
            if data.get("reviewId") != review_id:
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
            review.status = "completed"
            review.save()

            # Update review counts
            review.reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__in=["accepted", "rejected", "uncertain", "exemplary"],
            ).count()
            review.save()

            # Return success response
            return JsonResponse(
                {
                    "ok": True,
                    "finishedAt": datetime.utcnow().isoformat() + "Z",
                    "savePath": review.save_path if review.save_path else None,
                }
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


def export_review_results(request, review_id):
    """
    Export review annotations as JSON file.
    """
    try:
        # Convert string to UUID if needed
        if isinstance(review_id, str):
            try:
                review_id = uuid.UUID(review_id)
            except ValueError:
                return JsonResponse({"error": "Invalid review ID format"}, status=400)

        # Get the review with related tomograms
        review = Review.objects.select_related("msi_session", "requestor").get(review_id=review_id)

        # Get the reviewedOnly parameter
        reviewed_only = request.GET.get("reviewedOnly", "false").lower() == "true"

        # If reviewedOnly is true, allow export during review
        # If reviewedOnly is false, only allow export when review is completed
        if not reviewed_only and review.status != "completed":
            return JsonResponse({"error": "Review must be completed before exporting all tomograms"}, status=400)

        # Get tomograms for this review
        if reviewed_only:
            # Only get reviewed tomograms (not pending)
            tomograms = ReviewTomogram.objects.filter(
                review=review,
                quality__in=["accepted", "rejected", "uncertain", "exemplary"],
            )
        else:
            # Get all tomograms (including pending)
            tomograms = ReviewTomogram.objects.filter(review=review)

        # Format the export data
        export_data = {
            "review_id": str(review.review_id),
            "run_id": review.run_id,
            "review_name": review.review_name,
            "review_type": review.review_type,
            "total_count": review.total_count,
            "status": review.status,
            "created_at": review.created_at.isoformat(),
            "requestor_name": review.requestor.username if review.requestor else None,
            "objects_of_interest": review.objects_of_interest,
            "msi_session_name": review.msi_session.name,
            "reconstruction_type": review.reconstruction_type,
            "tomograms": [],
        }

        # Add tomogram annotations
        for tomogram in tomograms:
            annotation = {
                "tomogram_id": tomogram.tomogram_id,
                "quality": tomogram.quality if tomogram.quality else "pending",
                "rejection_reasons": tomogram.rejection_reasons if tomogram.rejection_reasons else [],
                "object_labels": tomogram.object_labels if tomogram.object_labels else [],
                "position_id": tomogram.position_id,
                "created_at": tomogram.created_at.isoformat(),
            }
            export_data["tomograms"].append(annotation)

        # Create the response with the JSON data
        response = JsonResponse(export_data)
        logger.debug(f"Exporting review {review_id} with {len(export_data['tomograms'])} tomograms")
        # Set headers for file download
        export_type = "reviewed_only" if reviewed_only else "complete"
        filename = f"review_{review_id}_{export_type}_export.json"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Type"] = "application/json"
        response["Content-Length"] = len(json.dumps(export_data))

        return response

    except Review.DoesNotExist:
        return JsonResponse({"error": "Review not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_review_tomograms(request, review_id):
    """
    Get all tomograms for a specific review.
    """
    logger.debug(f"Getting tomograms for review_id: {review_id} (type: {type(review_id).__name__})")

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

            logger.debug(f"Found review: {review.review_id}")
        except Review.DoesNotExist:
            logger.warning(f"Review not found with ID: {review_id}")
            # List all available review IDs for debugging
            all_reviews = Review.objects.all()
            available_ids = [(r.review_id, r.review_name) for r in all_reviews]
            logger.debug(f"Available review IDs: {available_ids}")
            return JsonResponse({"error": "Review not found"}, status=404)

        # Get tomograms for the review
        tomograms = ReviewTomogram.objects.filter(
            review=review,
        ).values("tomogram_id", "quality")

        logger.debug(f"Found {tomograms.count()} tomograms for review {review_id}")

        # Format the response
        tomograms_data = [
            {
                "tomogramId": tomo["tomogram_id"],
                "status": tomo["quality"] if tomo["quality"] else "pending",
            }
            for tomo in tomograms
        ]

        return JsonResponse(tomograms_data, safe=False)

    except Exception as e:
        logger.exception(f"Unexpected error in get_review_tomograms: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class ReviewTomogramView(View):
    """
    View for managing individual tomogram reviews.
    """

    def get(self, request, review_id, tomogram_id):
        """
        Get detailed information about a specific tomogram in a review.
        """
        logger.debug(f"Getting tomogram details for review_id: {review_id}, tomogram_id: {tomogram_id}")

        try:
            # First check if the review exists
            try:
                review = Review.objects.get(review_id=review_id)
                logger.debug(f"Found review: {review.review_id}")
            except Review.DoesNotExist:
                logger.warning(f"Review not found with ID: {review_id}")
                return JsonResponse({"error": "Review not found"}, status=404)

            # Get the specific tomogram
            try:
                tomogram = ReviewTomogram.objects.get(
                    review__review_id=review_id,
                    tomogram_id=tomogram_id,
                )
                logger.debug(f"Found tomogram: {tomogram.tomogram_id}")
            except ReviewTomogram.DoesNotExist:
                logger.warning(f"Tomogram not found with ID: {tomogram_id}")
                return JsonResponse({"error": "Tomogram not found"}, status=404)

            # Format the response
            response_data = {
                "tomogramId": tomogram.tomogram_id,
                "displayName": f"{tomogram.position_id}",
                "reconstructionType": review.reconstruction_type,
                "zarrPath": None,
                "existingReview": {
                    "quality": None,
                    "rejectionReasons": [],
                    "objectLabels": [],
                },
            }
            # Extract sessionid and runid from tomogram
            session_id = tomogram.session.name if tomogram.session else None
            run_id = tomogram.run_id if tomogram.run_id else None

            # Construct zarr path based on reconstruction type
            review = tomogram.review
            if review.reconstruction_type.lower() == "sart":
                vol_suffix = "vol003"
                job_name = "aretomo3"
            elif review.reconstruction_type.lower() == "dctf":
                vol_suffix = "vol001"
                job_name = "aretomo3"
            else:
                vol_suffix = ""  # denoised
                job_name = "denoise"

            # Resolve zarr URL against the review's cluster (falls back to the default cluster if not set).
            cluster = review.cluster or Cluster.get_default()
            if cluster is None:
                logger.warning("Review has no cluster and no default cluster is configured")
                return JsonResponse(
                    {"error": "No default cluster is configured. Set one in the admin (Stores → Clusters)."},
                    status=500,
                )
            response_data["zarrPath"] = resolve_review_path(
                "zarr_url",
                cluster=cluster,
                msi_session=tomogram.session,
                proc_software=job_name,
                proc_run=run_id,
                vol_suffix=vol_suffix,
                position=tomogram.position_id,
            )
            response_data["cluster"] = cluster.cluster_id

            zarr_fetch_url = resolve_review_path(
                "zarr_url",
                cluster=cluster,
                msi_session=tomogram.session,
                proc_software=job_name,
                proc_run=run_id,
                vol_suffix=vol_suffix,
                position=tomogram.position_id,
                backend_fetch=True,
            )

            logger.debug(f"Computing contrast limits for {review.reconstruction_type} reconstruction: {zarr_fetch_url}")
            try:
                contrast_limits = compute_optimal_contrast_limits(zarr_fetch_url, method="gmm")
                response_data["contrastLimits"] = contrast_limits
                response_data["contrastMethod"] = "gmm"
                response_data["contrastComputed"] = True
            except Exception as e:
                logger.warning(f"Failed to compute contrast limits: {e}")
                # Use default contrast limits if computation fails
                response_data["contrastLimits"] = [-0.05, 0.05]
                response_data["contrastMethod"] = "default"
                response_data["contrastComputed"] = False

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
            logger.exception(f"Unexpected error in GET tomogram: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)

    def post(self, request, review_id, tomogram_id):
        """
        Submit a review result for a specific tomogram.
        """
        logger.debug(f"Submitting review result for review_id: {review_id}, tomogram_id: {tomogram_id}")

        try:
            # Parse request body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            # Validate required fields
            if "quality" not in data:
                return JsonResponse({"error": "Missing required field: quality"}, status=400)

            # Validate quality value
            valid_qualities = ["accepted", "rejected", "uncertain", "exemplary", "pending"]
            if data["quality"] not in valid_qualities:
                return JsonResponse(
                    {"error": f"Invalid quality value. Must be one of: {', '.join(valid_qualities)}"}, status=400
                )

            # Get the tomogram
            try:
                tomogram = ReviewTomogram.objects.get(
                    review__review_id=review_id,
                    tomogram_id=tomogram_id,
                )
                logger.debug(f"Found tomogram: {tomogram.tomogram_id}")
            except ReviewTomogram.DoesNotExist:
                logger.warning(f"Tomogram not found with ID: {tomogram_id}")
                return JsonResponse({"error": "Tomogram not found"}, status=404)

            # Update tomogram review data
            tomogram.quality = data["quality"]

            # Handle rejection reasons - store as JSON string
            if data["quality"] == "rejected":
                tomogram.rejection_reasons = json.dumps(data["rejectionReasons"])
            else:
                tomogram.rejection_reasons = json.dumps([])

            # Handle object labels - store as JSON string
            if "objectLabels" in data:
                tomogram.object_labels = json.dumps(data["objectLabels"])

            # Save the changes
            tomogram.save()

            # Update review counts
            review = tomogram.review
            review.reviewed_count = ReviewTomogram.objects.filter(
                review=review,
                quality__in=["accepted", "rejected", "uncertain", "exemplary"],
            ).count()
            review.save()

            return JsonResponse({"ok": True})

        except Exception as e:
            logger.exception(f"Unexpected error in POST tomogram review: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
