import {
  ApiListResponse,
  FiltersList,
  GridData,
  SEARCH_PARAM_NAME,
  SearchParamValue,
} from "@/common/types";
import { FetchResponseInfo, TestFilterCategory } from "@/testing/types";
import { getSearchParamFirstValue } from "@/testing/utils";

const TEST_SORTABLE_GRID_FIELDS = [
  "grid",
  "cassette",
  "project",
  "puck",
  "user",
] as const;

export const GRID_A: GridData = {
  grid: {
    id: 0,
    name: "foo bar foo baz",
    trashed: false,
    url: "bazfoobazbazbarbar",
    createdAt: "2024-08-23T21:44:30.881Z",
    updatedAt: null,
  },
  cassette: {
    name: "bar baz foo foo",
  },
  project: {
    id: 0,
    name: "baz foo baz baz baz",
    url: "barfoofoobarbaz",
  },
  puck: {
    name: "baz foo baz",
  },
  user: {
    id: 0,
    name: "foo",
  },
  freezingPlan: {
    id: 0,
    sample: [{ id: 1, name: "foo baz bar foo", url: "bazfoobazbazbarbar" }],
  },
  freezingSession: {
    id: 0,
    createdAt: "2024-08-23T21:52:44.539Z",
  },
  screeningSession: "barbarfoobaz",
  msiSession: [
    {
      id: 0,
      name: "bar baz",
      url: "foobarfoofoo",
    },
  ],
};

export const GRID_B: GridData = {
  grid: {
    id: 1,
    name: "foo barbarbarbaz",
    trashed: false,
    url: "foofoobarfoofoo",
    createdAt: "2024-09-11T00:52:55.141Z",
    updatedAt: null,
  },
  cassette: {
    name: "bar foofoo bar bazbar",
  },
  project: {
    id: 1,
    name: "barbaz bazbar",
    url: "bazfoobarfoobarbar",
  },
  puck: {
    name: "foo bar baz foo barfoofoo",
  },
  user: {
    id: 1,
    name: "bazbaz bar bazfoo bar",
  },
  freezingPlan: {
    id: 1,
    sample: [{ id: 1, name: "bar baz bazfoo bazfoo", url: "foofoobarbar" }],
  },
  freezingSession: {
    id: 1,
    createdAt: "2024-09-11T00:53:04.340Z",
  },
  screeningSession: "barbazbazbaz",
  msiSession: [
    {
      id: 1,
      name: "foo baz baz bazfoobaz",
      url: "foofoofoobazfoobarbar",
    },
  ],
};

export const GRIDS = [GRID_A, GRID_B];

export const TEST_DEFAULT_GRIDS_PAGE_SIZE = 10;

export const URL_BASE = "http://localhost:8000";
export const URL_NONEXISTENT = "/nonexistent";
export const URL_GRIDS = "/cryo_grids/v1/grids";
export const URL_FILTERS_LIST = "/cryo_grids/v1/filterlist";
export const URL_FOO = "/foo";

export const FETCH_RESPONSE_FILTERS_LIST: FiltersList<TestFilterCategory> = {
  filters: {
    cassette: [
      {
        name: "foo bar foobaz baz",
        count: 2,
        selected: false,
      },
    ],
    date: [
      {
        name: "barfoobaz foobar bazbaz",
        count: 1,
        selected: true,
      },
      {
        name: "baz bar foofoo bar",
        count: 2,
        selected: false,
      },
    ],
    msiSession: [
      {
        name: "foo bazfoo barfoobar",
        count: 2,
        selected: false,
      },
    ],
    project: [
      {
        name: "bar baz foo bazbar",
        count: 3,
        selected: true,
      },
    ],
    puck: [
      {
        name: "bazbazbaz bar barfoo",
        count: 3,
        selected: true,
      },
      {
        name: "foobar baz foo",
        count: 2,
        selected: true,
      },
    ],
    sample: [
      {
        name: "bar bar barbar",
        count: 1,
        selected: false,
      },
    ],
    screeningSession: [
      {
        name: "foofoo baz foo",
        count: 2,
        selected: false,
      },
    ],
    status: [
      {
        name: "baz bar foo barbaz",
        count: 2,
        selected: false,
      },
    ],
    user: [
      {
        name: "foo baz foo bazbar",
        count: 1,
        selected: false,
      },
    ],
  },
};

export const FETCH_RESPONSES: Record<string, FetchResponseInfo> = {
  [URL_NONEXISTENT]: {
    status: 404,
  },
  [URL_GRIDS]: {
    body(url) {
      const responseGrids: GridData[] = GRIDS.slice();

      // Query parameters.
      const searchParamValue = url.searchParams.get(SEARCH_PARAM_NAME.QUERY);
      const values: SearchParamValue[] = JSON.parse(searchParamValue || "[]");

      // Sorting category values "sort" and "asc".
      const asc = getSearchParamFirstValue<boolean>(values, "asc", 0);
      const sort = getSearchParamFirstValue<string>(values, "sort", 0);
      const direction = asc ? 1 : -1;
      const sortKey = TEST_SORTABLE_GRID_FIELDS.find((key) => key === sort);
      // Sort grids by the first sort value and direction.
      if (sortKey) {
        responseGrids.sort(
          (a, b) => a[sortKey].name.localeCompare(b[sortKey].name) * direction,
        );
      }
      // Pagination category values "page" and "pageSize".
      const page = getSearchParamFirstValue<number>(
        values,
        "page",
        0,
        1,
      ) as number;
      const pageSize = getSearchParamFirstValue<number>(
        values,
        "pageSize",
        0,
        TEST_DEFAULT_GRIDS_PAGE_SIZE,
      ) as number;
      const pageStart = (page - 1) * pageSize;

      const responseData: ApiListResponse<GridData> = {
        pagination: {
          page,
          pageSize: pageSize,
          totalPages: Math.ceil(responseGrids.length / pageSize),
          totalResults: responseGrids.length,
        },
        result: responseGrids.slice(pageStart, pageStart + pageSize),
        sortBy: { asc: true, sort: "project" },
      };

      return JSON.stringify(responseData);
    },
  },
  [URL_FILTERS_LIST]: {
    body: JSON.stringify(FETCH_RESPONSE_FILTERS_LIST),
  },
  [URL_FOO]: {
    body(url) {
      return JSON.stringify(
        url.searchParams.get("q") === "true" ? "bar" : "foo",
      );
    },
  },
};
