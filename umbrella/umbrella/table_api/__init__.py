"""
Shared DRF machinery for the frontend's table contract.

The SDS table components (`EntityTable` / `TableStateProvider`) is custom:

- Request: a single ``q`` query param holding URI-encoded JSON of
  ``[{"category": ..., "value": ...}]``, carrying filters, page, sort and asc.
- Response: ``{"result": [...], "pagination": {...}, "sortBy": {...}}``.

Usage::

    class MyViewSet(viewsets.ReadOnlyModelViewSet):
        pagination_class = MyPagination      # subclass EntityTablePagination
        filter_backends = [TableQueryFilter]

        table_filters = {"project": "project__name__in"}
        table_search_fields = ["name"]
        table_sort_fields = {"name": "name", "count": "-item_count"}
        table_default_sort = ("name", True)
"""

from .filters import TableQueryFilter
from .pagination import EntityTablePagination, OrphanAwarePaginator
from .query import TableQuery, parse_table_query

__all__ = [
    "OrphanAwarePaginator",
    "EntityTablePagination",
    "TableQuery",
    "TableQueryFilter",
    "parse_table_query",
]
