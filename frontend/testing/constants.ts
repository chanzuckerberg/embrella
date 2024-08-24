import { Grid } from "../common/entities";
import { FetchResponse } from "./entities";

export const GRID_A: Grid = {
  grid: {
    id: 0,
    name: "foo bar foo baz",
    trashed: false,
    url: "bazfoobazbazbarbar",
    created: "2024-08-23T21:44:30.881Z",
  },
  cassette: {
    name: "bar baz foo foo",
  },
  project: {
    id: "barbazbarbaz",
    name: "baz foo baz baz baz",
    url: "barfoofoobarbaz",
  },
  puck: {
    name: "baz foo baz",
  },
  user: {
    id: "foofoo",
    name: "foo",
  },
  freezingPlan: {
    id: 0,
    sample: "foo baz bar foo",
  },
  freezingSession: {
    id: 0,
    created: "2024-08-23T21:52:44.539Z",
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

export const FETCH_RESPONSES: Record<string, FetchResponse> = {
  "http://localhost:8000/cryo_grids/v1/grids": {
    body: JSON.stringify({
      Results: [GRID_A],
    }),
  },
};
