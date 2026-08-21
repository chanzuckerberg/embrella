"""
Generic filter backend for the frontend's ``q`` table-query param.

Follows the DRF idiom of ``SearchFilter``/``OrderingFilter``:
configured by attributes declared on the view, rather than a subclass per
viewset.
"""

from collections.abc import Sequence

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.db.models.constants import LOOKUP_SEP
from rest_framework.filters import BaseFilterBackend

from .query import QUERY_PARAM, parse_table_query


def traverses_to_many(model, lookup: str) -> bool:
    """
    True if an ORM lookup path crosses a relation that can duplicate rows.
    """
    opts = model._meta
    for part in lookup.split(LOOKUP_SEP):
        try:
            field = opts.get_field(part)
        except FieldDoesNotExist:
            # Trailing lookup type (__in, __icontains) or an annotation name.
            break
        if not hasattr(field, "get_path_info"):
            break
        path_info = field.get_path_info()
        if any(path.m2m for path in path_info):
            return True
        opts = path_info[-1].to_opts
    return False


def q_lookups(q_object: Q) -> list[str]:
    """
    Every lookup path inside a ``Q``, including nested children.
    """
    lookups = []
    for child in q_object.children:
        if isinstance(child, Q):
            lookups.extend(q_lookups(child))
        elif isinstance(child, (list, tuple)) and child:
            lookups.append(child[0])
    return lookups


class TableQueryFilter(BaseFilterBackend):
    """
    Applies filters, search and ordering from the ``q`` param.

    View attributes:

    ``table_filters``
        ``{category: orm_lookup}``, e.g. ``{"project": "project__name__in"}``.
        or ``values -> Q`` for filters a single lookup can't express.
    ``table_search_fields``
        Fields matched with ``icontains`` for the ``search`` category: OR-ed
        across fields, AND-ed across terms.
    ``table_sort_fields``
        ``{column_id: ordering}`` where ordering is a field path or a sequence
        of them (a column can map to several expressions).
    ``table_default_sort``
        ``(column_id, asc)`` is default
    ``table_tiebreak``
        Appended to every ordering so paging is stable across ties. Defaults
        to ``"-pk"``.
    """

    def filter_queryset(self, request, queryset, view):
        queryset = self.filter_only(request, queryset, view)
        return self._apply_ordering(parse_table_query(request), queryset, view)

    def filter_only(self, request, queryset, view):
        """
        Filters and search, without ordering.

        For views that aggregate: Views that need
        the underlying rows for a page to nest them under their parent call
        this to get identically-filtered rows without inheriting a sort key
        """
        table_query = parse_table_query(request)

        queryset, filter_lookups = self._apply_filters(table_query, queryset, view)
        queryset, search_lookups = self._apply_search(table_query, queryset, view)

        applied = filter_lookups + search_lookups
        if any(traverses_to_many(queryset.model, lookup) for lookup in applied):
            queryset = queryset.distinct()

        return queryset

    def _apply_filters(self, table_query, queryset, view):
        """Returns the queryset and the ORM lookups that were applied."""
        table_filters = getattr(view, "table_filters", None) or {}
        applied = []

        for category, values in table_query.filters.items():
            lookup = table_filters.get(category)
            if not lookup or not values:
                continue
            if callable(lookup):
                q_object = lookup(values)
                queryset = queryset.filter(q_object)
                applied.extend(q_lookups(q_object))
            else:
                queryset = queryset.filter(**{lookup: values})
                applied.append(lookup)

        return queryset, applied

    def _apply_search(self, table_query, queryset, view):
        """
        AND across terms, OR across fields -- the same shape as DRF's
        SearchFilter. Within a term, any field may match.
        """
        search_fields = getattr(view, "table_search_fields", None) or []
        if not (table_query.search and search_fields):
            return queryset, []

        combined = Q()
        for term in table_query.search:
            term_q = Q()
            for search_field in search_fields:
                term_q |= Q(**{f"{search_field}__icontains": term})
            combined &= term_q

        return queryset.filter(combined), list(search_fields)

    def _apply_ordering(self, table_query, queryset, view):
        sort_fields = getattr(view, "table_sort_fields", None) or {}
        default_sort, default_asc = getattr(view, "table_default_sort", (None, True))
        tiebreak = getattr(view, "table_tiebreak", "-pk")

        column = table_query.sort if table_query.sort in sort_fields else default_sort
        asc = table_query.asc if table_query.asc is not None else default_asc

        # Record what was actually applied for paginator
        table_query.resolved_sort = column
        table_query.resolved_asc = asc

        expressions = sort_fields.get(column) if column else None
        if not expressions:
            return queryset.order_by(tiebreak) if tiebreak else queryset

        if isinstance(expressions, str):
            expressions = [expressions]
        elif not isinstance(expressions, Sequence):
            expressions = [str(expressions)]

        ordering = [expression if asc else f"-{expression}" for expression in expressions]
        if tiebreak:
            ordering.append(tiebreak)

        return queryset.order_by(*ordering)

    def get_schema_operation_parameters(self, view):
        """
        Describes ``q``.
        """
        categories = sorted((getattr(view, "table_filters", None) or {}).keys())
        sort_keys = sorted((getattr(view, "table_sort_fields", None) or {}).keys())

        lines = [
            "URI-encoded JSON list of `{category, value}` objects carrying filters, pagination and sort state.",
            "",
            "Reserved categories: `page` (int), `pageSize` (int), `sort` (column id), `asc` (bool), `search` (string).",
        ]
        if categories:
            lines.append(f"Filter categories: {', '.join(f'`{c}`' for c in categories)}.")
        if sort_keys:
            lines.append(f"Sortable column ids: {', '.join(f'`{s}`' for s in sort_keys)}.")
        lines.append('Example: `?q=[{"category":"page","value":[2]},{"category":"sort","value":["name"]}]`')

        return [
            {
                "name": QUERY_PARAM,
                "required": False,
                "in": "query",
                "description": "\n".join(lines),
                "schema": {"type": "string"},
            },
        ]
