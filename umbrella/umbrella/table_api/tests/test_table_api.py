"""
Tests for the shared table-query layer.

Deliberately model-free: the layer is exercised through a fake queryset and
`APIRequestFactory`, so it can be proven correct independently of any feature
that adopts it.
"""

import json

import pytest
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from umbrella.table_api import EntityTablePagination, TableQueryFilter, mark_selected, parse_table_query
from umbrella.table_api.filters import q_lookups, traverses_to_many


def q(items):
    """Encode a `q` param the way frontend/app/common/queries/utils.ts does."""
    return {"q": json.dumps(items)}


def make_request(params=None):
    return Request(APIRequestFactory().get("/", params or {}))


class FakeQuerySet(list):
    """
    Minimal queryset stand-in recording filter/order calls.

    ``model`` is a real model because the backend introspects lookup paths to
    decide whether ``distinct()`` is needed. User is convenient: ``username``
    is a local field and ``groups`` is a to-many, so one model covers both
    branches without touching the database.
    """

    model = User

    def __init__(self, items=(), ordering=None, filters=None, distinct_called=False):
        super().__init__(items)
        self.ordering = ordering or []
        self.filters = filters or []
        self.distinct_called = distinct_called

    def _clone(self, **overrides):
        state = {
            "items": list(self),
            "ordering": list(self.ordering),
            "filters": list(self.filters),
            "distinct_called": self.distinct_called,
        }
        state.update(overrides)
        return FakeQuerySet(**state)

    def filter(self, *args, **kwargs):
        return self._clone(filters=[*self.filters, kwargs or args])

    def order_by(self, *fields):
        return self._clone(ordering=list(fields))

    def distinct(self):
        return self._clone(distinct_called=True)

    def count(self):
        return len(self)


class FakeView:
    # `username` is a local field (no fan-out); `groups` is a to-many.
    table_filters = {"username": "username__in", "group": "groups__name__in"}
    table_search_fields = ["username", "first_name"]
    table_sort_fields = {"name": "username", "count": "item_count"}
    table_default_sort = ("name", True)


def run_filter(params=None, view=None, queryset=None):
    request = make_request(params)
    queryset = queryset if queryset is not None else FakeQuerySet()
    result = TableQueryFilter().filter_queryset(request, queryset, view or FakeView())
    return request, result


def paginate(params, items, view=None):
    """Run the filter then the paginator, returning the response body."""
    request, queryset = run_filter(params, view=view, queryset=FakeQuerySet(items))
    paginator = EntityTablePagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(page).data


class TestParsing:
    def test_absent_q_gives_defaults(self):
        parsed = parse_table_query(make_request())
        assert parsed.page == 1
        assert parsed.page_size is None
        assert parsed.sort is None
        assert parsed.filters == {}

    def test_malformed_json_raises_validation_error_not_500(self):
        with pytest.raises(ValidationError):
            parse_table_query(make_request({"q": "{not json"}))

    def test_non_list_q_rejected(self):
        with pytest.raises(ValidationError):
            parse_table_query(make_request({"q": json.dumps({"category": "page"})}))

    def test_non_dict_entry_rejected(self):
        with pytest.raises(ValidationError):
            parse_table_query(make_request(q(["page"])))

    @pytest.mark.parametrize("value", [[3], 3, ["3"], "3"])
    def test_page_accepts_scalar_list_and_string(self, value):
        parsed = parse_table_query(make_request(q([{"category": "page", "value": value}])))
        assert parsed.page == 3

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(True, True), ([True], True), ("true", True), (False, False), (["false"], False)],
    )
    def test_asc_accepts_bool_and_string(self, value, expected):
        parsed = parse_table_query(make_request(q([{"category": "asc", "value": value}])))
        assert parsed.asc is expected

    def test_first_load_empty_sort_arrays_do_not_crash(self):
        # TableStateProvider starts with sortState = [], so searchParam.ts
        # emits empty arrays for both categories on the very first request.
        parsed = parse_table_query(
            make_request(q([{"category": "sort", "value": []}, {"category": "asc", "value": []}])),
        )
        assert parsed.sort is None
        assert parsed.asc is None

    def test_parse_is_memoized_on_the_request(self):
        request = make_request(q([{"category": "page", "value": [2]}]))
        assert parse_table_query(request) is parse_table_query(request)


class TestFiltering:
    def test_known_filter_applied(self):
        _, result = run_filter(q([{"category": "username", "value": ["ada"]}]))
        assert {"username__in": ["ada"]} in result.filters

    def test_unknown_filter_category_ignored_not_400(self):
        _, result = run_filter(q([{"category": "nonsense", "value": ["x"]}]))
        assert result.filters == []
        assert result.distinct_called is False


class TestDistinct:
    """distinct() costs a sort/dedup, so only apply it where fan-out is possible."""

    def test_to_many_filter_triggers_distinct(self):
        _, result = run_filter(q([{"category": "group", "value": ["staff"]}]))
        assert result.distinct_called is True

    def test_to_one_filter_does_not(self):
        _, result = run_filter(q([{"category": "username", "value": ["ada"]}]))
        assert result.distinct_called is False

    def test_search_over_to_one_fields_does_not(self):
        _, result = run_filter(q([{"category": "search", "value": ["ada"]}]))
        assert result.filters, "search should still have been applied"
        assert result.distinct_called is False

    def test_mixed_filters_trigger_distinct_once(self):
        _, result = run_filter(
            q([{"category": "username", "value": ["ada"]}, {"category": "group", "value": ["staff"]}]),
        )
        assert result.distinct_called is True

    @pytest.mark.parametrize(
        ("lookup", "expected"),
        [
            ("username", False),
            ("username__in", False),
            ("first_name__icontains", False),
            ("groups__name__in", True),  # M2M
            ("logentry__object_repr", True),  # reverse FK also fans out
            ("not_a_field__in", False),  # unresolvable -> assume safe
        ],
    )
    def test_traverses_to_many(self, lookup, expected):
        assert traverses_to_many(User, lookup) is expected


class TestCallableFilters:
    """
    A `table_filters` value may be a callable returning a Q, for filters no
    single lookup can express -- see `_processing_software_q` in tem/viewsets.py.
    """

    class CallableView(FakeView):
        table_filters = {
            "username": "username__in",
            # Crosses a to-many on one side only.
            "either": lambda values: Q(username__in=values) | Q(groups__name__in=values),
            "local": lambda values: Q(username__in=values) | Q(first_name__in=values),
        }

    def test_callable_q_is_applied(self):
        _, result = run_filter(q([{"category": "either", "value": ["ada"]}]), view=self.CallableView())
        (applied,) = result.filters
        (condition,) = applied
        assert condition.connector == "OR"
        assert sorted(condition.children) == [("groups__name__in", ["ada"]), ("username__in", ["ada"])]

    def test_to_many_inside_the_q_still_triggers_distinct(self):
        # The whole point of q_lookups: a callable must not silently opt out of
        # the fan-out protection a string lookup gets for free.
        _, result = run_filter(q([{"category": "either", "value": ["ada"]}]), view=self.CallableView())
        assert result.distinct_called is True

    def test_all_to_one_q_does_not_trigger_distinct(self):
        _, result = run_filter(q([{"category": "local", "value": ["ada"]}]), view=self.CallableView())
        assert result.distinct_called is False

    def test_string_lookups_are_unaffected(self):
        _, result = run_filter(q([{"category": "username", "value": ["ada"]}]), view=self.CallableView())
        assert {"username__in": ["ada"]} in result.filters
        assert result.distinct_called is False

    def test_q_lookups_walks_nested_children(self):
        nested = Q(a__in=[1]) | (Q(b="x") & Q(c__isnull=True))
        assert sorted(q_lookups(nested)) == ["a__in", "b", "c__isnull"]


class TestMarkSelected:
    def test_marks_only_the_selected_values(self):
        options = [{"name": "aretomo3", "count": 2}, {"name": "denoise", "count": 1}]
        assert mark_selected(options, ["denoise"]) == [
            {"name": "aretomo3", "count": 2, "selected": False},
            {"name": "denoise", "count": 1, "selected": True},
        ]

    def test_comparison_is_case_and_whitespace_insensitive(self):
        options = [{"name": "AreTomo3", "count": 1}]
        assert mark_selected(options, [" aretomo3 "])[0]["selected"] is True

    def test_no_selection_marks_everything_false(self):
        options = [{"name": "aretomo3", "count": 1}]
        assert mark_selected(options, None)[0]["selected"] is False


class TestSearch:
    def test_single_term_ors_across_fields(self):
        _, result = run_filter(q([{"category": "search", "value": ["ada"]}]))
        (applied,) = result.filters
        (condition,) = applied
        assert condition.connector == "OR"
        assert set(condition.children) == {
            ("username__icontains", "ada"),
            ("first_name__icontains", "ada"),
        }

    def test_multiple_terms_are_anded_not_ored(self):
        # Matches DRF's SearchFilter. OR-ing terms would mean typing a second
        # word *widened* the result set, which no search box should do.
        _, result = run_filter(q([{"category": "search", "value": ["ada", "lovelace"]}]))
        (applied,) = result.filters
        (condition,) = applied
        assert condition.connector == "AND"
        assert len(condition.children) == 2
        assert all(child.connector == "OR" for child in condition.children)


class TestOrdering:
    def test_default_sort_applied_with_tiebreak(self):
        _, result = run_filter()
        assert result.ordering == ["username", "-pk"]

    def test_descending_sort(self):
        _, result = run_filter(
            q([{"category": "sort", "value": ["count"]}, {"category": "asc", "value": [False]}]),
        )
        assert result.ordering == ["-item_count", "-pk"]

    def test_multi_expression_sort_flips_every_expression(self):
        # The shape natural-name sorting needs: one column id mapping to
        # several ordering expressions, all flipped together on descending.
        class MultiView(FakeView):
            table_sort_fields = {"natural": ["name_is_numeric", "name_as_number", "username"]}
            table_default_sort = ("natural", True)

        _, asc = run_filter(view=MultiView())
        assert asc.ordering == ["name_is_numeric", "name_as_number", "username", "-pk"]

        _, desc = run_filter(q([{"category": "asc", "value": [False]}]), view=MultiView())
        assert desc.ordering == ["-name_is_numeric", "-name_as_number", "-username", "-pk"]

    def test_unknown_sort_falls_back_and_echoes_the_fallback(self):
        request, _ = run_filter(q([{"category": "sort", "value": ["bogus"]}]))
        resolved = parse_table_query(request)
        assert resolved.resolved_sort == "name"


class TestResponseShape:
    def test_response_keys_exactly(self):
        body = paginate(None, list(range(5)))
        assert list(body.keys()) == ["result", "pagination", "sortBy"]
        assert list(body["pagination"].keys()) == ["page", "pageSize", "totalPages", "totalResults"]
        assert list(body["sortBy"].keys()) == ["sort", "asc"]

    def test_sort_by_echoes_resolved_sort(self):
        body = paginate(q([{"category": "sort", "value": ["bogus"]}]), list(range(3)))
        assert body["sortBy"] == {"sort": "name", "asc": True}

    def test_page_beyond_last_clamps_to_200_not_404(self):
        body = paginate(
            q([{"category": "page", "value": [99]}, {"category": "pageSize", "value": [10]}]),
            list(range(25)),
        )
        assert body["pagination"]["page"] == body["pagination"]["totalPages"]

    def test_page_size_honored_and_clamped_at_max(self):
        body = paginate(q([{"category": "pageSize", "value": [5]}]), list(range(20)))
        assert body["pagination"]["pageSize"] == 5
        assert len(body["result"]) == 5

        body = paginate(q([{"category": "pageSize", "value": [9999]}]), list(range(20)))
        assert body["pagination"]["pageSize"] == EntityTablePagination.max_page_size

    def test_orphans_absorbs_the_tail_page(self):
        # 31 rows at pageSize 28: the 3-row tail is <= orphans, so it joins
        # page 1 rather than becoming a page of its own.
        body = paginate(q([{"category": "pageSize", "value": [28]}]), list(range(31)))
        assert body["pagination"]["totalPages"] == 1
        assert body["pagination"]["totalResults"] == 31
        assert len(body["result"]) == 31

    def test_total_results_is_not_total_pages_times_page_size(self):
        # The invariant clients must respect: derive nothing from the product.
        body = paginate(q([{"category": "pageSize", "value": [25]}]), list(range(171)))
        pagination = body["pagination"]
        assert pagination["totalResults"] == 171
        assert pagination["totalPages"] * pagination["pageSize"] == 175
