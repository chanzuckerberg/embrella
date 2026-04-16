"""
Shared helper functions for cryo_grids ViewSets.
"""

from datetime import datetime, timedelta
from functools import reduce

from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.db.models.functions import Cast

from cryo_grids.models import CryoGrid, Label


def natural_name_annotations(field="name"):
    """Return annotation kwargs for natural (numeric-first) sorting on a name field.

    Usage: queryset.annotate(**natural_name_annotations("puck__name"))
    """
    return {
        "name_is_numeric": Case(
            When(**{f"{field}__regex": r"^\d+$"}, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        "name_as_number": Case(
            When(**{f"{field}__regex": r"^\d+$"}, then=Cast(field, IntegerField())),
            default=Value(None),
            output_field=IntegerField(),
        ),
    }


def natural_name_ordering(name_field="name", desc=False):
    """Return order_by args for natural sorting, given the name column to fall back to.

    Usage: queryset.order_by(*natural_name_ordering("filter_name"))
    """
    if desc:
        return ("-name_is_numeric", "-name_as_number", f"-{name_field}")
    return ("name_is_numeric", "name_as_number", name_field)


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


def build_shared_grid_inventory_q_objects(q_params, grid_prefix=""):
    """Build Q objects for filter categories shared across GridInventory tabs.

    Handles: project, user, sample, label, msiSession, cassette, date,
    screeningSession, status.

    Does NOT handle entity-specific filters: puck, search.

    Args:
        q_params: List of dicts with 'category' and 'value' keys.
        grid_prefix: ORM lookup prefix to reach CryoGrid fields
            (e.g., "" for CryoGrid, "cryogrid__" for CryoGridBox,
             "cryogridbox__cryogrid__" for Puck).

    Returns:
        List of Q objects (caller decides AND vs OR combination).
    """
    filter_mappings = {
        "project": f"{grid_prefix}intended_project__name__in",
        "cassette": f"{grid_prefix}grid_cassette__name__in",
        "msiSession": f"{grid_prefix}msisession__name__in",
        "screeningSession": f"{grid_prefix}atlassession__group__name__in",
        "status": f"{grid_prefix}trashed__in",
        "label": f"{grid_prefix}labels__name__in",
        "sample": f"{grid_prefix}specimen__samples__name__in",
    }

    date_mapping = {
        "last_1_month": 1,
        "last_3_months": 3,
        "last_6_months": 6,
    }

    q_objects = []

    for filter_item in q_params:
        category = filter_item.get("category")
        values = filter_item.get("value")

        if category in ("page", "pageSize", "sort", "asc", "filterType"):
            continue

        if category in filter_mappings:
            field = filter_mappings[category]
            if values is None or (isinstance(values, list) and None in values):
                q_objects.append(Q(**{f"{field.split('__')[0]}__isnull": True}))
            elif values:
                if not isinstance(values, list):
                    values = [values]
                if category == "status":
                    status_map = {"Active": False, "Inactive": True}
                    values = [status_map.get(v, v) for v in values]
                q_objects.append(Q(**{field: values}))
        elif category == "user" and values:
            usernames = values if isinstance(values, list) else [values]
            q_username_filters = Q()
            for username in usernames:
                if "@" in username:
                    username = username.split("@")[0]
                q_username_filters |= Q(**{f"{grid_prefix}user__username__icontains": username})
            q_objects.append(q_username_filters)
        elif category == "date" and values:
            date_value = values[0] if isinstance(values, list) else values
            if date_value in date_mapping:
                months = date_mapping[date_value]
                now_dt = datetime.now()
                start_date = now_dt - timedelta(days=months * 30)
                q_objects.append(Q(**{f"{grid_prefix}updated_on__gte": start_date}))

    return q_objects


def apply_shared_grid_inventory_filters(queryset, q_params, grid_prefix=""):
    """Apply shared GridInventory filters to a queryset (AND combination).

    Convenience wrapper around build_shared_grid_inventory_q_objects.
    """
    q_objects = build_shared_grid_inventory_q_objects(q_params, grid_prefix)
    if q_objects:
        combined = reduce(lambda x, y: x & y, q_objects, Q())
        queryset = queryset.filter(combined).distinct()
    return queryset


def get_shared_filterlist_options(base_qs, grid_prefix=""):
    """Generate filter options for categories shared across GridInventory tabs.

    Args:
        base_qs: Base queryset for the entity (CryoGrid, CryoGridBox, or Puck).
        grid_prefix: ORM lookup prefix to reach CryoGrid fields.

    Returns:
        Dict of filter category → list of {name, count} dicts.
    """

    def query_filter(filter_expr, value_expr):
        rows = list(
            base_qs.filter(**{filter_expr: False})
            .values(filter_name=F(value_expr))
            .annotate(count=Count("id", distinct=True))
            .order_by("filter_name")
        )
        return [{"name": r["filter_name"], "count": r["count"]} for r in rows]

    return {
        "project": query_filter(f"{grid_prefix}intended_project__isnull", f"{grid_prefix}intended_project__name"),
        "sample": query_filter(f"{grid_prefix}specimen__samples__isnull", f"{grid_prefix}specimen__samples__name"),
        "user": query_filter(f"{grid_prefix}user__isnull", f"{grid_prefix}user__username"),
        "label": query_filter(f"{grid_prefix}labels__isnull", f"{grid_prefix}labels__name"),
        "cassette": query_filter(f"{grid_prefix}grid_cassette__isnull", f"{grid_prefix}grid_cassette__name"),
        "msiSession": query_filter(f"{grid_prefix}msisession__isnull", f"{grid_prefix}msisession__name"),
        "screeningSession": query_filter(
            f"{grid_prefix}atlassession__group__isnull", f"{grid_prefix}atlassession__group__name"
        ),
        "status": [
            {
                "name": "Active",
                "count": base_qs.filter(**{f"{grid_prefix}trashed": False}).distinct().count(),
            },
            {
                "name": "Inactive",
                "count": base_qs.filter(**{f"{grid_prefix}trashed": True}).distinct().count(),
            },
        ],
    }


def parse_selected_filters(q_params):
    """Parse q_params into a dict of category → set of selected values."""
    selected = {}
    for item in q_params:
        category = item.get("category")
        values = item.get("value")
        if category and values:
            selected[category] = set(values if isinstance(values, list) else [values])
    return selected


def apply_grid_box_filters(queryset, q_params):
    """
    Apply filters to a CryoGridBox queryset based on q_params.
    Uses shared helpers for grid-related filters and adds grid-box-specific
    filters (puck, search).
    """
    q_objects = build_shared_grid_inventory_q_objects(q_params, grid_prefix="cryogrid__")

    for filter_item in q_params:
        category = filter_item.get("category")
        values = filter_item.get("value")

        if category == "puck" and values:
            if values is None or (isinstance(values, list) and None in values):
                q_objects.append(Q(puck__isnull=True))
            else:
                if not isinstance(values, list):
                    values = [values]
                q_objects.append(Q(puck__name__in=values))
        elif category == "search" and values:
            search_terms = values if isinstance(values, list) else [values]
            search_q = Q()
            for search_term in search_terms:
                if search_term:
                    term_q = (
                        Q(name__icontains=search_term)
                        | Q(cryogrid__name__icontains=search_term)
                        | Q(cryogrid__intended_project__name__icontains=search_term)
                        | Q(cryogrid__user__username__icontains=search_term)
                        | Q(cryogrid__specimen__samples__name__icontains=search_term)
                        | Q(cryogrid__labels__name__icontains=search_term)
                    )
                    if search_term.isdigit():
                        term_q |= Q(cryogrid__id=int(search_term))
                    search_q |= term_q
            if search_q:
                q_objects.append(search_q)

    if q_objects:
        combined = reduce(lambda x, y: x & y, q_objects, Q())
        queryset = queryset.filter(combined).distinct()

    return queryset
