import { ApiListResponse, FiltersList, GridData } from "@/common/types";
import { FetchResponseInfo } from "@/testing/types";

export const GRID_A: GridData = {
  grid: {
    id: 0,
    name: "foo bar foo baz",
    trashed: false,
    url: "bazfoobazbazbarbar",
    createdAt: "2024-08-23T21:44:30.881Z",
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

export const URL_NONEXISTENT = "http://localhost:8000/nonexistent";
export const URL_GRIDS = "http://localhost:8000/cryo_grids/v1/grids";
export const URL_FILTERS_LIST = "http://localhost:8000/cryo_grids/v1/filterslist";
export const URL_FOO = "http://localhost:8000/foo";

const FETCH_RESPONSE_GRIDS: ApiListResponse<GridData> = {
  result: [GRID_A],
};

export const FETCH_RESPONSE_FILTERS_LIST: FiltersList = {
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
    body: JSON.stringify(FETCH_RESPONSE_GRIDS),
  },
  [URL_FILTERS_LIST]: {
    body: JSON.stringify(FETCH_RESPONSE_FILTERS_LIST),
  },
  [URL_FOO]: {
    body: JSON.stringify("foo"),
  },
};
