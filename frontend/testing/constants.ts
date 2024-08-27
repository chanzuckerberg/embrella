import { GridData } from "../common/entities";
import { FetchResponseInfo } from "./entities";

export const GRID_A: GridData = {
  grid: {
    id: 0,
    name: "foo bar foo baz",
    trashed: false,
    url: "bazfoobazbazbarbar",
    created_at: "2024-08-23T21:44:30.881Z",
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
    created_at: "2024-08-23T21:52:44.539Z",
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

export const FETCH_RESPONSES: Record<string, FetchResponseInfo> = {
  "http://localhost:8000/nonexistent": {
    status: 404,
  },
  "http://localhost:8000/cryo_grids/v1/grids": {
    body: JSON.stringify({
      Result: [GRID_A],
    }),
  },
  "http://localhost:8000/foo": {
    body: JSON.stringify("foo"),
  },
};
