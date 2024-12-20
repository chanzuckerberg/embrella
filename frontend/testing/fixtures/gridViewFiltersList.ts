import { FiltersList } from "@app/common/types/filter";
import { TestFilterCategory } from "@testing/types";

/**
 * Partial test data representing a list of filters typed as `TestFilterCategory`.
 * This dataset contains all filters in an unselected state.
 * - The "cassette" category includes multiple options, all unselected.
 * - The "msiSession" category includes two session options, both unselected.
 */
export const INITIAL_FILTERS_LIST = {
  filters: {
    cassette: [
      {
        name: "cassette 01",
        count: 1,
        selected: false,
      },
      {
        name: null,
        count: 1,
        selected: false,
      },
      {
        name: false,
        count: 1,
        selected: false,
      },
    ],
    msiSession: [
      {
        name: "msi session 01",
        count: 1,
        selected: false,
      },
      {
        name: "msi session 02",
        count: 1,
        selected: false,
      },
    ],
  },
} as FiltersList<TestFilterCategory>;

/**
 * Partial test data representing a list of filters, typed as `TestFilterCategory`.
 * This dataset includes a selected "cassette" category filter with one selected value
 * and additional filters for other categories.
 * - The "cassette" category contains multiple filter options, with "cassette 01" selected.
 * - The "msiSession" category contains a single unselected filter option.
 */
export const SELECTED_FILTERS_LIST = {
  filters: {
    cassette: [
      {
        name: "cassette 01",
        count: 1,
        selected: true,
      },
      {
        name: "cassette 02",
        count: 1,
        selected: false,
      },
      {
        name: null,
        count: 1,
        selected: false,
      },
      {
        name: false,
        count: 1,
        selected: false,
      },
    ],
    msiSession: [
      {
        name: "msi session 01",
        count: 1,
        selected: false,
      },
    ],
  },
} as FiltersList<TestFilterCategory>;
