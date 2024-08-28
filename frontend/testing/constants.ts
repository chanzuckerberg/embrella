import { ApiListResponse, GridData } from "../common/entities";
import { FetchResponseInfo } from "./entities";

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
    sample: ["foo baz bar foo"],
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
export const URL_FOO = "http://localhost:8000/foo";

const FETCH_RESPONSE_GRIDS: ApiListResponse<GridData> ={
  result: [GRID_A],
};

export const FETCH_RESPONSES: Record<string, FetchResponseInfo> = {
  [URL_NONEXISTENT]: {
    status: 404,
  },
  [URL_GRIDS]: {
    body: JSON.stringify(FETCH_RESPONSE_GRIDS),
  },
  [URL_FOO]: {
    body: JSON.stringify("foo"),
  },
};
