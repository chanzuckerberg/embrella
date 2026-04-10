import json
import logging
import os
import re

# python library import
from datetime import datetime
from functools import reduce

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from pydantic import ValidationError
from stores.models import Path

# project app imports

from .forms import CopyGridForm, NumberToCopyGridForm
from .models import CryoGrid, CryoGridBox, GridLabel, Specimen
from .utils import (
    CassetteModel,
    CryoGridsQueryParams,
    FreezingSessionModel,
    GridModel,
    MSISessionModel,
    PaginationMetadataModel,
    ProjectModel,
    PuckModel,
    SortMetadataModel,
    UnprocessableEntity,
    UserModel,
)

# from umbrella.settings import ENVIRONMENT
logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv("DJANGO_ENV", "development")


def get_frontend_url():
    """Get the frontend URL based on environment"""
    environment = os.getenv("DJANGO_ENV", "development")
    if environment == "staging":
        return "http://umbrella-dev.czbiohub.org/"
    elif environment == "production":
        return "http://umbrella.czbiohub.org/"
    else:  # development
        return "http://localhost:3000/"


def build_frontend_url_with_state(request, base_path="/samples/grid_logging"):
    """Build frontend URL with state parameters from request"""
    frontend_url = f"{get_frontend_url()}{base_path}"

    # Get state parameters from request (check both GET and POST)
    state_params = []

    # User ID state
    return_user_id = request.GET.get("return_user_id") or request.POST.get("return_user_id")
    if return_user_id:
        state_params.append(f"user_id={return_user_id}")

    # Puck ID state
    return_puck_id = request.GET.get("return_puck_id") or request.POST.get("return_puck_id")
    if return_puck_id:
        state_params.append(f"puck_id={return_puck_id}")

    # Slot position state
    return_slot_position = request.GET.get("return_slot_position") or request.POST.get("return_slot_position")
    if return_slot_position:
        state_params.append(f"slot_position={return_slot_position}")

    # Grid position state
    return_grid_position = request.GET.get("return_grid_position") or request.POST.get("return_grid_position")
    if return_grid_position:
        state_params.append(f"grid_position={return_grid_position}")

    # Grid ID state
    return_grid_id = request.GET.get("return_grid_id") or request.POST.get("return_grid_id")
    if return_grid_id:
        state_params.append(f"grid_id={return_grid_id}")

    # Add state parameters to URL if any exist
    if state_params:
        frontend_url += "?" + "&".join(state_params)

    # no owner to show all pucks
    frontend_url += "&owner=false"

    return frontend_url


def msi_session_sort_key(name):
    """
    Custom sorting function for MSI session names in format 'yymmmdda'.
    Returns a tuple for sorting with newer sessions first.
    """
    try:
        # Extract components from the name
        year = int(name[:2])
        month = name[2:5].lower()  # Convert to lowercase for consistent comparison
        day = int(name[5:7])
        seq = name[7] if len(name) > 7 else "a"  # Default to 'a' if no sequence letter

        # Convert month to number for proper sorting
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        # Check if month is valid
        if month not in month_map:
            return (0, 0, 0, "z")  # Move invalid months to the end

        month_num = month_map[month]

        # Validate year and day
        if not (0 <= year <= 99) or not (1 <= day <= 31):
            return (0, 0, 0, "z")  # Move invalid dates to the end

        # Return tuple for sorting (negative year for descending order - newer first)
        return (-year, -month_num, -day, seq)
    except (ValueError, IndexError):
        # If name doesn't match expected format, put it at the end
        return (0, 0, 0, "z")


def get_base_url():
    if ENVIRONMENT == "staging":
        return "http://umbrella-dev.czbiohub.org"
    elif ENVIRONMENT == "production":
        return "http://umbrella.czbiohub.org"
    else:  # development
        return "http://localhost:8000"


from django.views.decorators.csrf import csrf_exempt


# If you want to test locally, you can comment out the @login_required decorator
# @login_required
@require_http_methods(["GET"])
def get_cryo_grids_details(request):
    """
    Retrieves details about the grid with pagination and sorting
    """
    try:
        raw_q_param = request.GET.get("q", None)
        if raw_q_param:
            try:
                q_param = json.loads(raw_q_param)
            except json.JSONDecodeError as e:
                return JsonResponse({"error": f"Invalid JSON format for q parameter: {str(e)}"}, status=400)
        else:
            q_param = []

        query_data = request.GET.dict()
        query_data["q"] = q_param

        try:
            query_params = CryoGridsQueryParams(**query_data)
        except ValidationError as e:
            raise UnprocessableEntity(detail=f"Validation error: {str(e)}")

        sort_field = "updated_on"
        asc = False
        page_size = 10

        def extract_value(value):
            if isinstance(value, list) and len(value) > 0:
                value = value[0]
            return value

        # Detect sort, asc, pageSize from 'q' filters:
        for item in q_param:
            if item["category"] == "sort":
                # Map 'modifiedOn' to 'updated_on'
                raw_sort_val = extract_value(item["value"])
                sort_field = "updated_on" if raw_sort_val == "modifiedOn" else raw_sort_val
            elif item["category"] == "asc":
                asc_value = extract_value(item["value"])
                asc = bool(asc_value) if isinstance(asc_value, bool) else asc_value.lower() == "true"
            elif item["category"] == "pageSize":
                try:
                    page_size = int(extract_value(item["value"]))
                except ValueError:
                    return JsonResponse({"error": "Invalid value for page_size, must be an integer"}, status=400)

        sort_order = sort_field if asc else f"-{sort_field}"

        # Base queryset (NO prefetch for 'specimen__sample' since it's a CharField)
        queryset = (
            CryoGrid.objects.select_related(
                "intended_project",
                "freezing_session",
                "grid_box__puck",
                "user",
                "grid_cassette",
                "specimen",
            )
            .prefetch_related(
                "msisession",
                "atlassession__group",
                "labels",
            )
            .values(
                "id",
                grid_name=F("name"),
                cassette_name=F("grid_cassette__name"),
                project_name=F("intended_project__name"),
                project_id=F("intended_project__id"),
                puck=F("grid_box__puck__name"),
                userID=F("user__id"),
                username=F("user__username"),
                status=F("trashed"),
                created_on=F("create_on"),
                grid_updated_on=F("updated_on"),
                msisession_id=F("msisession__id"),
                msisession_name=F("msisession__name"),
                fz_session_id=F("freezing_session__id"),
                fz_session_datetime=F("freezing_session__datetime"),
                specimen_uniq_id=F("specimen__id"),
                screening_session_name=F("atlassession__group__name"),
                label_id=F("labels__id"),
                label_name=F("labels__name"),
                label_color=F("labels__color"),
            )
            .order_by(sort_order, "-id")
        )

        # Apply custom filters
        queryset = apply_filters(queryset, query_params.q)

        # Format to dictionary
        formatted_result = format_queryset_results(queryset)

        # Check if sample name filtering is requested
        sample_filter = next((item for item in q_param if item["category"] == "sample"), None)
        if sample_filter:
            # 'value' could be a list or a single string
            sample_name_input = (
                sample_filter["value"] if isinstance(sample_filter["value"], list) else [sample_filter["value"]]
            )
            formatted_result = filter_by_sample_name(formatted_result, sample_name_input)

        # Convert final dict to list
        formatted_grid_list = list(formatted_result.values())

        # Pagination
        page_param = next((item for item in q_param if item["category"] == "page"), None)
        page_size_param = next((item for item in q_param if item["category"] == "pageSize"), None)

        page = int(page_param["value"][0]) if page_param else 1
        page_size = int(page_size_param["value"][0]) if page_size_param else page_size

        paginator = Paginator(formatted_grid_list, page_size, orphans=3)

        try:
            paginated_queryset = paginator.page(page)
        except PageNotAnInteger:
            paginated_queryset = paginator.page(1)
        except EmptyPage:
            paginated_queryset = paginator.page(paginator.num_pages)

        if not paginated_queryset.object_list:
            return JsonResponse({"result": []}, status=200)

        response_data = {
            "result": paginated_queryset.object_list,
            "pagination": PaginationMetadataModel(
                page=paginated_queryset.number,
                pageSize=int(page_size),
                totalPages=paginator.num_pages,
                totalResults=paginator.count,
            ).model_dump(),
            "sortBy": SortMetadataModel(
                sort="modifiedOn" if sort_field == "updated_on" else sort_field,
                asc=asc,
            ).model_dump(),
        }

        return JsonResponse(response_data)
    except UnprocessableEntity as e:
        return JsonResponse({"error": e.detail}, status=e.status_code)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)


def apply_filters(queryset, filters):
    """
    Apply filters to a CryoGrid queryset based on a list of filter items.
    Uses shared helpers for common categories and adds grid-specific filters
    (puck, search, filterType).
    """
    from cryo_grids.viewset_helpers import build_shared_grid_inventory_q_objects

    filter_q_objects = build_shared_grid_inventory_q_objects(filters, grid_prefix="")

    filter_type = "AND"

    for filter_item in filters:
        category = filter_item.get("category")
        values = filter_item.get("value")

        if category == "filterType" and values:
            filter_type = values[0].upper() if isinstance(values, list) else values.upper()
        elif category == "puck" and values:
            if values is None or (isinstance(values, list) and None in values):
                filter_q_objects.append(Q(grid_box__puck__isnull=True))
            else:
                if not isinstance(values, list):
                    values = [values]
                filter_q_objects.append(Q(grid_box__puck__name__in=values))
        elif category == "search" and values:
            search_terms = values if isinstance(values, list) else [values]
            search_q = Q()
            for search_term in search_terms:
                if search_term:
                    search_q |= (
                        Q(name__icontains=search_term)
                        | Q(intended_project__name__icontains=search_term)
                        | Q(user__username__icontains=search_term)
                        | Q(specimen__samples__name__icontains=search_term)
                        | Q(msisession__name__icontains=search_term)
                        | Q(labels__name__icontains=search_term)
                    )
            if search_q:
                filter_q_objects.append(search_q)

    q_filters = Q()
    if filter_q_objects:
        if filter_type == "OR":
            q_filters = reduce(lambda x, y: x | y, filter_q_objects, Q())
        else:
            q_filters = reduce(lambda x, y: x & y, filter_q_objects, Q())

    return queryset.filter(q_filters).distinct()


def format_queryset_results(queryset):
    formatted_result = {}
    for item in queryset:
        grid_id = item["id"]
        fz_session_datetime = (
            item["fz_session_datetime"].strftime("%Y-%m-%d %H:%M") if item["fz_session_datetime"] else None
        )
        if grid_id not in formatted_result:
            formatted_result[grid_id] = {
                "grid": format_grid(item).model_dump(),
                "cassette": format_cassette(item).model_dump(),
                "project": format_project(item).model_dump(),
                "puck": format_puck(item).model_dump(),
                "user": format_user(item).model_dump(),
                "specimen": format_specimen(item),
                "freezingSession": format_freezing_session(item).model_dump(),
                "screeningSession": item["screening_session_name"],
                "msiSession": [],
                "labels": [],
            }
        # Attach MSI session
        if item["msisession_id"]:
            add_msi_session(formatted_result[grid_id]["msiSession"], item)

        # Attach label
        if item.get("label_id"):
            existing_label_ids = {l["id"] for l in formatted_result[grid_id]["labels"]}
            if item["label_id"] not in existing_label_ids:
                formatted_result[grid_id]["labels"].append(
                    {
                        "id": item["label_id"],
                        "name": item["label_name"],
                        "color": item["label_color"],
                    }
                )

    return formatted_result


def get_specimen_list(specimen_id):
    try:
        specimen = Specimen.objects.get(id=specimen_id)
        specimen_list = []
        base_url = get_base_url()
        for sample in specimen.samples.all():
            sample_url = f"{base_url}/admin/cryo_grids/specimen/{sample.id}"
            specimen_list.append(
                {
                    "id": sample.id,
                    "name": sample.name,
                    "url": sample_url,
                }
            )
        return specimen_list
    except ObjectDoesNotExist:
        return []


def extract_parts(text):
    if not text or not isinstance(text, str):  # Ensure text is not None or non-string
        return "", []

    # Try extracting the main part safely
    main_match = re.match(r"^[^\(\[,]+", text)
    main_part = main_match.group(0).strip() if main_match else text.strip()  # Use full text if match fails

    # # Extract all words (tags) but remove main_part if present
    # tags = re.findall(r'\b\w+\b', text)
    # tags = [tag for tag in tags if tag.lower() != main_part.lower()]  # Case-insensitive removal

    return main_part  # , sorted(tags)  # Sorting ensures consistent comparison


def are_equivalent(text1, text2):
    return extract_parts(text1) == extract_parts(text2)


def filter_by_sample_name(formatted_result, sample_name_input):
    """
    Filter the final data by matching any of the specimen's sample names.
    """
    matching_results = {}

    if not sample_name_input or not isinstance(sample_name_input, list):
        return matching_results

    for grid_id, data in formatted_result.items():
        samples = data["specimen"].get("samples", [])
        # Check if any sample's name is equivalent to any of the filter values
        if any(
            are_equivalent(sample.get("name", ""), filter_value)
            for sample in samples
            for filter_value in sample_name_input
        ):
            matching_results[grid_id] = data

    return matching_results


def format_grid(item):
    base_url = get_base_url()
    grid_url = f"{base_url}/cryo_grids/grid_detail/{item['id']}"
    return GridModel(
        id=item["id"],
        name=f"{item['grid_name']} (id={item['id']})",
        trashed=item["status"],
        url=grid_url,
        createdAt=item["created_on"].isoformat() if item["created_on"] else None,
        updatedAt=item["grid_updated_on"].isoformat() if item["grid_updated_on"] else None,
    )


def format_cassette(item):
    return CassetteModel(name=item["cassette_name"])


def format_project(item):
    base_url = get_base_url()
    project_url = f"{base_url}/admin/projects/project/{item['project_id']}"
    return ProjectModel(id=item["project_id"], name=item["project_name"], url=project_url)


def format_puck(item):
    return PuckModel(name=item["puck"])


def format_user(item):
    return UserModel(
        id=item["userID"], name=item["username"].split("@")[0] if "@" in item["username"] else item["username"]
    )


def get_specimen_info(specimen_id):
    try:
        specimen = Specimen.objects.get(id=specimen_id)
        base_url = get_base_url()
        samples_list = []
        for sample in specimen.samples.all():
            sample_url = f"{base_url}/admin/cryo_grids/specimen/{sample.id}"
            samples_list.append(
                {
                    "id": sample.id,
                    "name": sample.name,
                    "url": sample_url,
                }
            )
        # Extract all sample names
        sample_names = [sample["name"] for sample in samples_list]

        return {
            "id": specimen.id,
            "name": f"Specimen ({', '.join(sample_names)})" if sample_names else "Specimen (no samples)",
            "samples": samples_list,
        }
    except ObjectDoesNotExist:
        return {}


def format_specimen(item):
    return get_specimen_info(item["specimen_uniq_id"])


def format_freezing_session(item):
    if item["fz_session_id"] and item["fz_session_datetime"]:
        return FreezingSessionModel(id=item["fz_session_id"], createdAt=str(item["fz_session_datetime"]))
    else:
        return FreezingSessionModel(id=None, createdAt=None)


def add_msi_session(msi_session_list, item):
    base_url = get_base_url()
    msi_session_entry = MSISessionModel(
        id=item["msisession_id"],
        name=item["msisession_name"],
        url=f"{base_url}/legacy/tem/{item['msisession_id']}",
    ).model_dump()
    if msi_session_entry not in msi_session_list:
        msi_session_list.append(msi_session_entry)


def grid_detail_view(request, grid_id=1, error_msg=""):
    """
    View to show grid detail and provide forms to link to admin grid editing
    and grid copying
    """
    form = CopyGridForm()
    number_form = NumberToCopyGridForm
    old_grid = CryoGrid.objects.get(id=grid_id)
    field_objs = old_grid._meta.get_fields()
    fields = {}
    for f in field_objs:
        if f.related_model == Path:
            continue
        try:
            fields[f.name] = getattr(old_grid, f.name)
        except AttributeError:
            # reverse ManyToOneRel such as processes.procrun is not in this model
            continue
        # ManyToManyField
        if hasattr(fields[f.name], "all"):
            fields[f.name] = list(map((lambda x: x.__str__()), fields[f.name].all()))
    context = {"old_grid": old_grid, "fields": fields, "form": form, "number_form": number_form, "error_msg": error_msg}
    return render(request, "cryo_grids/grid_detail.html", context)


def _save_copied_grid(old_grid, box, position, number_of_copies=1):
    # grids sharing the same unique requirement except copy_number
    existing_grids = CryoGrid.objects.filter(
        name=old_grid.name, freezing_session=old_grid.freezing_session, specimen=old_grid.specimen
    )
    existing_numbers = list(map((lambda x: x.copy_number), existing_grids))

    # Find the next available copy numbers
    max_existing = max(existing_numbers) if existing_numbers else 0
    new_copy_numbers = list(range(max_existing + 1, max_existing + 1 + number_of_copies))

    created_grids = []

    # Create multiple grids if number_of_copies > 1
    for i, copy_number in enumerate(new_copy_numbers):
        new_grid = CryoGrid.objects.get(id=old_grid.id)
        new_grid.id = None
        new_grid.grid_cassette = None
        new_grid.slot_number_in_cassette = None
        new_grid.trashed = False
        new_grid.grid_box = box
        new_grid.position_in_box = position + i  # Increment position for each copy
        new_grid.copy_number = copy_number
        new_grid.create_on = datetime.today()
        new_grid.updated_on = datetime.today()
        new_grid.save()

        # Copy labels from the original grid
        for gl in GridLabel.objects.filter(grid=old_grid):
            GridLabel.objects.create(grid=new_grid, label=gl.label, added_by=gl.added_by)

        created_grids.append(new_grid)

    return created_grids[0] if len(created_grids) == 1 else created_grids


def _handle_grid_to_copy_post(request):
    """
    Validate parameters and save copied grids
    """
    old_grid_id = int(request.POST["old_grid"])
    old_grid = CryoGrid.objects.get(id=old_grid_id)
    new_grid_box_id = int(request.POST["new_box"])
    number_to_copy = int(request.POST["number_to_copy"])
    box = CryoGridBox.objects.get(id=new_grid_box_id)
    # validate
    grids_at_used_positions = CryoGrid.objects.filter(grid_box=box, trashed=False)
    used_positions = list(map((lambda x: x.position_in_box), grids_at_used_positions))
    new_positions = list(set(range(1, box.max_grids + 1)).difference(used_positions))
    new_positions.sort()
    if number_to_copy > len(new_positions):
        error_msg = 'Box "%s" has only %d position(s) left.  Not enough to put in %d grids. Please try again.' % (
            box,
            len(new_positions),
            number_to_copy,
        )
        return HttpResponseRedirect(
            reverse("cryo_grids:grid_detail", kwargs={"grid_id": old_grid_id, "error_msg": error_msg})
        )

    # Create multiple copies at once
    if number_to_copy > 1:
        # Use the updated _save_copied_grid function
        created_grids = _save_copied_grid(old_grid, box, new_positions[0], number_to_copy)
    else:
        # Single copy
        for p in new_positions[:number_to_copy]:
            _save_copied_grid(old_grid, box, p)

    frontend_url = build_frontend_url_with_state(request)
    return HttpResponseRedirect(frontend_url)


def copy_grid_to_box(request, error_msg=""):
    """
    TODO this work around error message passing.  There may be a better way.
    """
    if request.method == "POST":
        return _handle_grid_to_copy_post(request)



@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_grid_trashed_status(request, grid_id):
    """
    Update the trashed status of a specific grid
    """
    try:
        grid = CryoGrid.objects.get(id=grid_id)

        # Parse JSON data instead of form data
        import json

        data = json.loads(request.body)
        trashed_status = data.get("trashed", False)

        # Update the trashed status
        grid.trashed = trashed_status

        # If trashing, remove from grid box (and thus puck hierarchy)
        if trashed_status:
            grid.grid_box = None
            grid.position_in_box = None

        grid.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Grid {'trashed' if trashed_status else 'restored'} successfully",
                "trashed": grid.trashed,
            }
        )

    except CryoGrid.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "Grid not found",
            },
            status=404,
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )
    try:
        grid = CryoGrid.objects.get(id=grid_id)

        # Parse JSON data instead of form data
        import json

        data = json.loads(request.body)
        trashed_status = data.get("trashed", False)

        # Update the trashed status
        grid.trashed = trashed_status

        # If trashing, remove from grid box (and thus puck hierarchy)
        if trashed_status:
            grid.grid_box = None
            grid.position_in_box = None

        grid.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Grid {'trashed' if trashed_status else 'restored'} successfully",
                "trashed": grid.trashed,
            }
        )

    except CryoGrid.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "Grid not found",
            },
            status=404,
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500,
        )


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_grid_clipped_status(request, grid_id):
    try:
        grid = CryoGrid.objects.get(id=grid_id)
        data = json.loads(request.body)
        clipped_status = data.get("clipped", False)

        grid.clipped = clipped_status
        grid.save()

        grid.refresh_from_db()
        return JsonResponse(
            {
                "success": True,
                "message": f"Grid {'clipped' if clipped_status else 'unclipped'} successfully",
                "clipped": grid.clipped,
            }
        )
    except CryoGrid.DoesNotExist:
        return JsonResponse({"success": False, "error": "Grid not found"}, status=404)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_available_positions(request, object_id):
    """AJAX endpoint to get available positions for a selected box."""
    try:
        box = CryoGridBox.objects.get(pk=object_id)
        max_grids = box.max_grids or 4
        used_positions = list(
            CryoGrid.objects.filter(
                grid_box=box,
                trashed=False,
            ).values_list("position_in_box", flat=True)
        )

        all_positions = list(range(1, max_grids + 1))
        available_positions = [pos for pos in all_positions if pos not in used_positions]
        max_positions = len(available_positions)

        print(f"Box: {box.name}, Max grids: {max_grids}")  # Debug log
        print(f"Used positions: {used_positions}")  # Debug log
        print(f"Available positions: {available_positions}")  # Debug log
        print(f"Max positions: {max_positions}")  # Debug log

        return JsonResponse(
            {
                "max_positions": max_positions,
                "available_positions": available_positions,
            }
        )
    except CryoGridBox.DoesNotExist:
        return JsonResponse({"max_positions": 0, "error": "Box not found"})
