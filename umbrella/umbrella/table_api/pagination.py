"""
Pagination for the frontend's EntityTable component.

`EntityTablePagination` builds the entire response body, not just the page
slice, because EntityTable reads ``result``, ``pagination`` and ``sortBy``
from one object (see ``useFetchTableData``).
"""

from collections import OrderedDict

from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.paginator import Paginator as DjangoPaginator
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .query import parse_table_query


class OrphanAwarePaginator(DjangoPaginator):
    """
    Django's Paginator with ``orphans`` preset.

    DRF instantiates the paginator positionally as ``(object_list, per_page)``
    """

    default_orphans = 3

    def __init__(self, object_list, per_page, **kwargs):
        kwargs.setdefault("orphans", self.default_orphans)
        super().__init__(object_list, per_page, **kwargs)


class EntityTablePagination(PageNumberPagination):
    """
    Builds the body for EntityTable:
    ``{"result": [...], "pagination": {...}, "sortBy": {...}}``.
    """

    page_size = 25
    max_page_size = 200
    django_paginator_class = OrphanAwarePaginator

    def get_page_size(self, request):
        """Read pageSize out of the `q` param, clamped to max_page_size."""
        requested = parse_table_query(request).page_size
        if requested is None:
            return self.page_size
        if requested <= 0:
            return self.page_size
        if self.max_page_size:
            return min(requested, self.max_page_size)
        return requested

    def get_page_number(self, request, paginator):
        """
        Also clamps out-of-range pages instead of 404ing.
        """
        page_number = parse_table_query(request).page
        if page_number < 1:
            return 1
        if page_number > paginator.num_pages:
            return paginator.num_pages
        return page_number

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        self.request = request
        try:
            self.page = paginator.page(self.get_page_number(request, paginator))
        except (PageNotAnInteger, EmptyPage):
            # get_page_number clamps, so this is belt-and-braces for an empty
            # queryset where num_pages is 1 but the page has no rows.
            self.page = paginator.page(1)
        return list(self.page)

    def get_paginated_response(self, data):
        table_query = parse_table_query(self.request)
        paginator = self.page.paginator
        return Response(
            OrderedDict(
                [
                    ("result", data),
                    (
                        "pagination",
                        OrderedDict(
                            [
                                ("page", self.page.number),
                                ("pageSize", self.get_page_size(self.request)),
                                ("totalPages", paginator.num_pages),
                                ("totalResults", paginator.count),
                            ],
                        ),
                    ),
                    (
                        "sortBy",
                        OrderedDict(
                            [
                                ("sort", table_query.resolved_sort),
                                ("asc", table_query.resolved_asc),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def get_paginated_response_schema(self, schema):
        """Without this, the schema advertises DRF's count/next/previous/results."""
        return {
            "type": "object",
            "required": ["result", "pagination", "sortBy"],
            "properties": {
                "result": schema,
                "pagination": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "example": 1},
                        "pageSize": {"type": "integer", "example": self.page_size},
                        "totalPages": {"type": "integer", "example": 7},
                        "totalResults": {
                            "type": "integer",
                            "example": 171,
                            "description": (
                                "Total matching rows. Do not derive this from "
                                "totalPages * pageSize -- they are not equal."
                            ),
                        },
                    },
                },
                "sortBy": {
                    "type": "object",
                    "properties": {
                        "sort": {
                            "type": "string",
                            "nullable": True,
                            "description": "Column id actually sorted on, after whitelist validation.",
                        },
                        "asc": {"type": "boolean"},
                    },
                },
            },
        }

    def get_schema_operation_parameters(self, view):
        """
        No pagination params of our own to document. for DRF
        """
        return []
