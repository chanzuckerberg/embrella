"""DRF ViewSets for the people directory app.

- **people** — directory entries (``Person``), deduplicated by ORCID iD. Each
  person has an optional single ``institution``.
- **institutions** — organizations (``Institution``) people are affiliated with.

All routes require an authenticated session. List endpoints are
paginated (``page``/``page_size`` query params) and both resources support a
``search`` query param for type-ahead lookups.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from people.models import Institution, Person
from people.serializers import (
    InstitutionSerializer,
    PersonSerializer,
)


class PeoplePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500


@extend_schema_view(
    list=extend_schema(
        summary="List people",
        description=(
            "Return a paginated directory of people, ordered by family then given name. "
            "Each entry nests the person's full institution object (or null). "
            "Pass `search` to match against given name, family name, ORCID iD, or contact email — "
            "intended for author/contributor autocomplete."
        ),
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Case-insensitive substring match on given_name, family_name, orcid, and contact_email.",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Get a person",
        description="Return a single directory entry with its full institution object nested inline.",
    ),
    create=extend_schema(
        summary="Create a person",
        description=(
            "Create a directory entry. `orcid` is optional and must be formatted as "
            "`xxxx-xxxx-xxxx-xxxx`; a blank value is stored as NULL so multiple entries "
            "without an ORCID don't collide, and a duplicate ORCID is rejected with a 400. "
            "`institution_id` optionally sets the person's institution by id; the response "
            "nests the full institution object back."
        ),
    ),
    update=extend_schema(
        summary="Replace a person", description="Full update of a directory entry (all writable fields required)."
    ),
    partial_update=extend_schema(
        summary="Update a person", description="Partial update of a directory entry (only the supplied fields change)."
    ),
    destroy=extend_schema(summary="Delete a person", description="Remove a directory entry."),
)
class PersonViewSet(viewsets.ModelViewSet):
    """CRUD for directory people, with search for author/contributor."""

    queryset = Person.objects.select_related("institution").order_by("family_name", "given_name")
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PeoplePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["given_name", "family_name", "orcid", "contact_email"]

    @extend_schema(
        summary="Get several people by id",
        description=(
            "Return the directory entries for a set of ids in one request — for "
            "resolving a stored list of people (e.g. an author list) back to full records. "
            "Pass the ids as a repeated or comma-separated `ids` query param "
            "(`?ids=1,2,3` or `?ids=1&ids=2`). Unknown ids are silently skipped, so the "
            "response may be shorter than the request; results are ordered by family then "
            "given name (not by request order) and each entry nests its full institution object. "
            "This response is not paginated."
        ),
        parameters=[
            OpenApiParameter(
                name="ids",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                many=True,
                required=True,
                description="Person ids to fetch. Repeat the param or comma-separate the values.",
            ),
        ],
        responses={200: PersonSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="by-ids", filter_backends=[], pagination_class=None)
    def by_ids(self, request):
        """Bulk-fetch people for an explicit list of ids (resolve a stored people list to records)."""
        raw = request.query_params.getlist("ids")
        # Accept both repeated (?ids=1&ids=2) and comma-separated (?ids=1,2) forms.
        tokens = [token for value in raw for token in value.split(",") if token.strip()]
        if not tokens:
            raise ValidationError({"ids": "Provide at least one person id."})
        try:
            ids = {int(token) for token in tokens}
        except ValueError:
            raise ValidationError({"ids": "All ids must be integers."})

        people = self.get_queryset().filter(pk__in=ids)
        return Response(self.get_serializer(people, many=True).data)


@extend_schema_view(
    list=extend_schema(
        summary="List institutions",
        description=(
            "Return a paginated list of institutions, ordered by name. "
            "Pass `search` to match against the institution name or ROR id."
        ),
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Case-insensitive substring match on name and ror_id.",
            ),
        ],
    ),
    retrieve=extend_schema(summary="Get an institution", description="Return a single institution."),
    create=extend_schema(
        summary="Create an institution",
        description="Create an institution. `name` is required; `ror_id` and address fields are optional.",
    ),
    update=extend_schema(summary="Replace an institution", description="Full update of an institution."),
    partial_update=extend_schema(summary="Update an institution", description="Partial update of an institution."),
    destroy=extend_schema(
        summary="Delete an institution",
        description=(
            "Delete an institution. Any people affiliated with it have their `institution` "
            "set to NULL (the link is severed, the people are kept)."
        ),
    ),
)
class InstitutionViewSet(viewsets.ModelViewSet):
    """CRUD for institutions, with search on name and ROR id."""

    queryset = Institution.objects.order_by("name")
    serializer_class = InstitutionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PeoplePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "ror_id"]
