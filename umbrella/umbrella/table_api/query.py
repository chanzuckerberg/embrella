"""
Parsing for the frontend's ``q`` table-query param.

The param is URI-encoded JSON: a list of ``{"category": ..., "value": ...}``
entries mixing filters with pagination and sort state. See
``frontend/app/common/utils/searchParam.ts`` for the encoder.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from rest_framework.exceptions import ValidationError

# Query param carrying the encoded table state. Also referenced by filters.py
# when documenting `q` for the OpenAPI schema.
QUERY_PARAM = "q"

# Cached parse, to carry between DRF hooks. Example: TableQuery resolved_sort
_CACHE_ATTR = "_embrella_table_query"


@dataclass
class TableQuery:
    """Parsed ``q`` param, plus the sort the filter backend actually applied."""

    filters: dict[str, list[Any]] = field(default_factory=dict)
    search: list[str] = field(default_factory=list)
    page: int = 1
    page_size: int | None = None
    sort: str | None = None
    asc: bool | None = None

    # Written by TableQueryFilter once it has validated `sort`
    resolved_sort: str | None = None
    resolved_asc: bool = True


def _as_list(value: Any) -> list[Any]:
    """Coerce a category value to a list; the frontend sends both forms."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _first(values: list[Any]) -> Any:
    """First element, or None. Sort/asc arrive as [] before the user sorts."""
    return values[0] if values else None


def _to_int(value: Any, default: int | None) -> int | None:
    """Ints may arrive as ints or numeric strings depending on the round-trip."""
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any, default: bool | None) -> bool | None:
    """`asc` is a JSON bool from searchParam.ts but a string via nuqs."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1"):
            return True
        if lowered in ("false", "0"):
            return False
    return default


def parse_table_query(request) -> TableQuery:
    """
    Parse (and memoize) the ``q`` param for this request.

    Raises ValidationError -- a 400, not a 500 -- on malformed input.
    Unknown categories are collected as filters rather than rejected: the
    frontend routinely ships a new filter id before the backend supports it,
    and the filter backend ignores categories it doesn't recognize.
    """
    cached = getattr(request, _CACHE_ATTR, None)
    if cached is not None:
        return cached

    raw = request.query_params.get(QUERY_PARAM) if hasattr(request, "query_params") else request.GET.get(QUERY_PARAM)

    parsed = TableQuery()
    if not raw:
        setattr(request, _CACHE_ATTR, parsed)
        return parsed

    try:
        items = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({QUERY_PARAM: f"Malformed JSON in '{QUERY_PARAM}': {exc}"}) from exc

    if not isinstance(items, list):
        raise ValidationError({QUERY_PARAM: f"'{QUERY_PARAM}' must be a JSON list of {{category, value}} objects."})

    for item in items:
        if not isinstance(item, dict):
            raise ValidationError(
                {QUERY_PARAM: f"Each '{QUERY_PARAM}' entry must be an object with 'category' and 'value'."},
            )

        category = item.get("category")
        if not category or not isinstance(category, str):
            continue

        values = _as_list(item.get("value"))

        # These five categories carry table state; everything else is a filter.
        if category == "page":
            parsed.page = _to_int(_first(values), 1) or 1
        elif category == "pageSize":
            parsed.page_size = _to_int(_first(values), None)
        elif category == "sort":
            sort = _first(values)
            parsed.sort = sort if isinstance(sort, str) and sort else None
        elif category == "asc":
            parsed.asc = _to_bool(_first(values), None)
        elif category == "search":
            parsed.search = [str(v) for v in values if v not in (None, "")]
        elif values:
            # Empty values mean "no constraint".
            parsed.filters[category] = values

    setattr(request, _CACHE_ATTR, parsed)
    return parsed
