"""
Building blocks for ``filterlist`` actions.

The frontend's filter sidebar (``EntityTableFilters``) fetches
``{"filters": {category: [{"name", "count", "selected"}]}}``
"""

from django.db.models import Count, F

from .query import parse_table_query


def value_counts(queryset, expression, *, count="pk", exclude_blank=True) -> list[dict]:
    """
    ``[{"name": ..., "count": ...}]`` for one filter category, ordered by name.

    ``expression`` is an ORM path or a query expression naming the option.
    ``count`` is the path to whatever should be counted once per option --
    ``"pk"`` for the queryset's own rows, or e.g. ``"msi_session"`` when
    reading options off a child table but counting distinct parents.

    Nulls are always dropped; blanks also unless ``exclude_blank=False``
    """
    option = expression if hasattr(expression, "resolve_expression") else F(expression)

    rows = queryset.annotate(_option=option).exclude(_option__isnull=True)
    if exclude_blank:
        rows = rows.exclude(_option="")

    rows = rows.values("_option").annotate(_count=Count(count, distinct=True)).order_by("_option")

    return [{"name": row["_option"], "count": row["_count"]} for row in rows]


def mark_selected(options: list[dict], selected_values) -> list[dict]:
    """
    Set ``selected`` on each option, in place, and return the list.
    note: compared case-insensitively
    """
    selected = {str(value).strip().lower() for value in (selected_values or ())}

    for option in options:
        name = option["name"]
        option["selected"] = name is not None and str(name).strip().lower() in selected

    return options


def build_filters(request, options_by_category: dict[str, list[dict]]) -> dict:
    """
    Apply the request's selections to already-counted options.

    ``options_by_category`` maps filter category -> the output of ``value_counts``.
    """
    selected_by_category = parse_table_query(request).filters

    return {
        category: mark_selected(options, selected_by_category.get(category))
        for category, options in options_by_category.items()
    }
