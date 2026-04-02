"""
Shared helper functions for cryo_grids ViewSets.
"""

from datetime import datetime, timedelta
from functools import reduce

from django.db.models import Q

from cryo_grids.models import CryoGrid, Label


def msi_session_sort_key(name):
    """
    Custom sorting function for MSI session names in format 'yymmmdda'.
    Returns a tuple for sorting with newer sessions first.
    """
    try:
        year = int(name[:2])
        month = name[2:5].lower()
        day = int(name[5:7])
        seq = name[7] if len(name) > 7 else "a"

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
        month_num = month_map.get(month, 0)
        return (-year, -month_num, -day, seq)
    except (ValueError, IndexError):
        return (0, 0, 0, name)


def add_selected_status(filter_list, category, selected_filters):
    """Mark filter items as selected based on the current filter state."""
    selected_values = selected_filters.get(category, set())
    if None in selected_values:
        for item in filter_list:
            item["selected"] = item["name"] is None
    else:
        for item in filter_list:
            item_name = item["name"]
            if isinstance(item_name, bool):
                item["selected"] = item_name in selected_values
            elif isinstance(item_name, str):
                item["selected"] = item_name.strip().lower() in {
                    val.lower() for val in selected_values if isinstance(val, str)
                }
            else:
                item["selected"] = False


def get_shared_search_suggestions(term, limit=5):
    """Shared search suggestions for project, user, sample, msiSession, label."""
    suggestions = []

    for name in (
        CryoGrid.objects.filter(intended_project__name__icontains=term)
        .values_list("intended_project__name", flat=True)
        .distinct()[:limit]
    ):
        if name:
            suggestions.append({"value": name, "category": "project"})

    for username in (
        CryoGrid.objects.filter(user__username__icontains=term)
        .values_list("user__username", flat=True)
        .distinct()[:limit]
    ):
        if username:
            display = username.split("@")[0] if "@" in username else username
            suggestions.append({"value": display, "category": "user"})

    for name in (
        CryoGrid.objects.filter(specimen__samples__name__icontains=term)
        .values_list("specimen__samples__name", flat=True)
        .distinct()[:limit]
    ):
        if name:
            suggestions.append({"value": name, "category": "sample"})

    for name in (
        CryoGrid.objects.filter(msisession__name__icontains=term)
        .values_list("msisession__name", flat=True)
        .distinct()[:limit]
    ):
        if name:
            suggestions.append({"value": name, "category": "msiSession"})

    for name in Label.objects.filter(name__icontains=term).values_list("name", flat=True).distinct()[:limit]:
        if name:
            suggestions.append({"value": name, "category": "label"})

    return suggestions


def apply_grid_box_filters(queryset, q_params):
    """
    Apply filters to a CryoGridBox queryset based on q_params.
    Filters grid boxes by their contained grids using reverse relationships.
    """
    filter_mappings = {
        "project": "cryogrid__intended_project__name__in",
        "cassette": "cryogrid__grid_cassette__name__in",
        "puck": "puck__name__in",
        "msiSession": "cryogrid__msisession__name__in",
        "screeningSession": "cryogrid__atlassession__group__name__in",
        "status": "cryogrid__trashed__in",
        "label": "cryogrid__labels__name__in",
        "sample": "cryogrid__specimen__samples__name__in",
    }

    date_mapping = {
        "last_1_month": 1,
        "last_3_months": 3,
        "last_6_months": 6,
    }

    filter_q_objects = []

    for filter_item in q_params:
        category = filter_item.get("category")
        values = filter_item.get("value")

        # Skip pagination/sort params
        if category in ("page", "pageSize", "sort", "asc", "filterType"):
            continue

        if category in filter_mappings:
            field = filter_mappings[category]
            if values is None or (isinstance(values, list) and None in values):
                filter_q_objects.append(Q(**{f"{field.split('__')[0]}__isnull": True}))
            elif values:
                if not isinstance(values, list):
                    values = [values]
                if category == "status":
                    status_map = {"Active": False, "Inactive": True}
                    values = [status_map.get(v, v) for v in values]
                filter_q_objects.append(Q(**{field: values}))
        elif category == "user" and values:
            usernames = values if isinstance(values, list) else [values]
            q_username_filters = Q()
            for username in usernames:
                if "@" in username:
                    username = username.split("@")[0]
                q_username_filters |= Q(cryogrid__user__username__icontains=username)
            filter_q_objects.append(q_username_filters)
        elif category == "search" and values:
            search_terms = values if isinstance(values, list) else [values]
            search_q = Q()
            for search_term in search_terms:
                if search_term:
                    search_q |= (
                        Q(name__icontains=search_term)
                        | Q(cryogrid__name__icontains=search_term)
                        | Q(cryogrid__intended_project__name__icontains=search_term)
                        | Q(cryogrid__user__username__icontains=search_term)
                        | Q(cryogrid__specimen__samples__name__icontains=search_term)
                        | Q(cryogrid__labels__name__icontains=search_term)
                    )
            if search_q:
                filter_q_objects.append(search_q)
        elif category == "date" and values:
            date_value = values[0] if isinstance(values, list) else values
            if date_value in date_mapping:
                months = date_mapping[date_value]
                now_dt = datetime.now()
                start_date = now_dt - timedelta(days=months * 30)
                filter_q_objects.append(Q(cryogrid__updated_on__gte=start_date))

    if filter_q_objects:
        combined = reduce(lambda x, y: x & y, filter_q_objects, Q())
        queryset = queryset.filter(combined).distinct()

    return queryset
