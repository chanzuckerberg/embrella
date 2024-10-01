import { reducer } from "@/views/GridsView/common/store/reducer";
import { INITIAL_STATE } from "@/views/GridsView/common/store/constants";
import {
  Action,
  ActionKind,
} from "@/views/GridsView/common/store/actions/types";
import {
  INITIAL_FILTERS_LIST,
  SELECTED_FILTERS_LIST,
} from "@/testing/fixtures/gridViewFiltersList";
import { SortBy } from "@/common/types";
import { State } from "@/views/GridsView/common/store/types";

const CATEGORY_UPDATED_AT = "updatedAt";
const CATEGORY_CASSETTE = "cassette";
const CATEGORY_CASSETTE_SINGLE_VALUE = ["cassette 01"];
const CATEGORY_CASSETTE_MULTIPLE_VALUES = ["cassette 01", "cassette 02"];
const FILTER_STATE_WITH_SINGLE_CATEGORY_VALUE: State["filterState"] = {
  [CATEGORY_CASSETTE]: CATEGORY_CASSETTE_SINGLE_VALUE,
};
const FILTER_STATE_WITH_MULTIPLE_CATEGORY_VALUES: State["filterState"] = {
  [CATEGORY_CASSETTE]: CATEGORY_CASSETTE_MULTIPLE_VALUES,
};
const SORT_BY: SortBy = {
  asc: false,
  sort: CATEGORY_UPDATED_AT,
};
const SORT_STATE: State["sortState"] = [
  { desc: true, id: CATEGORY_UPDATED_AT },
];

const MOCK_UPDATER_OR_VALUE = jest.fn(() => SORT_STATE);

describe("GridView Reducer", () => {
  it("should return state when action is unknown", () => {
    const action = {
      type: "UNKNOWN_ACTION",
      payload: undefined,
    } as unknown as Action;
    const state = reducer(INITIAL_STATE, action);
    expect(state).toEqual(INITIAL_STATE);
  });
  describe("filter update action", () => {
    it("should update filter state with selected category value", () => {
      const nextState = reducer(INITIAL_STATE, {
        payload: {
          categoryFilter: {
            category: CATEGORY_CASSETTE,
            value: CATEGORY_CASSETTE_SINGLE_VALUE,
          },
          filtersList: INITIAL_FILTERS_LIST,
        },
        type: ActionKind.UpdateFilterAction,
      });
      expect(nextState).toEqual({
        ...INITIAL_STATE,
        filterState: FILTER_STATE_WITH_SINGLE_CATEGORY_VALUE,
      });
    });
    it("should update filter state with unselected category", () => {
      const nextState = reducer(INITIAL_STATE, {
        payload: {
          categoryFilter: {
            category: CATEGORY_CASSETTE,
            value: [],
          },
          filtersList: SELECTED_FILTERS_LIST,
        },
        type: ActionKind.UpdateFilterAction,
      });
      expect(nextState).toEqual(INITIAL_STATE);
    });
    it("should update filter state with single selected category value, with multiple selected category values", () => {
      const nextState = reducer(INITIAL_STATE, {
        payload: {
          categoryFilter: {
            category: CATEGORY_CASSETTE,
            value: CATEGORY_CASSETTE_MULTIPLE_VALUES,
          },
          filtersList: SELECTED_FILTERS_LIST,
        },
        type: ActionKind.UpdateFilterAction,
      });
      expect(nextState).toEqual({
        ...INITIAL_STATE,
        filterState: FILTER_STATE_WITH_MULTIPLE_CATEGORY_VALUES,
      });
    });
  });
  describe("sort update action", () => {
    it("should update sort state with selected sort value", () => {
      const nextState = reducer(INITIAL_STATE, {
        payload: {
          sortBy: SORT_BY,
          updaterOrValue: MOCK_UPDATER_OR_VALUE,
        },
        type: ActionKind.UpdateSortAction,
      });
      expect(nextState).toEqual({
        ...INITIAL_STATE,
        sortState: SORT_STATE,
      });
    });
  });
});
