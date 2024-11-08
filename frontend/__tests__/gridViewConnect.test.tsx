import { useConnect } from "@/views/GridsView/components/Main/connect";
import { renderHook } from "@testing-library/react";
import { State } from "@/views/GridsView/common/store/types";
import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids/useFetchGrids";
import { useFetchFilters } from "@/views/GridsView/hooks/useFetchFilters/useFetchFilters";
import { StateContext } from "@/views/GridsView/common/store";
import React, { ReactNode } from "react";
import {
  buildFilterListSearchParam,
  buildGridListSearchParam,
  getFilterSearchParamValue,
  getPaginationSearchParamValue,
  getSortSearchParamValue,
} from "@/views/GridsView/components/Main/utils";
import { SearchParam, SearchParamValue } from "@/app/common/types/types";

const FILTER_SEARCH_PARAM_VALUES: SearchParamValue[] = [
  {
    category: "project",
    value: ["project 01", "project 02"],
  },
];
const PAGE_SEARCH_PARAM_VALUES: SearchParamValue[] = [
  { category: "page", value: [1] },
];
const SORT_SEARCH_PARAM_VALUES: SearchParamValue[] = [
  {
    category: "asc",
    value: [true],
  },
  {
    category: "sort",
    value: ["modifiedOn"],
  },
];
const GRID_LIST_SEARCH_PARAM: SearchParam = {
  q: [
    ...FILTER_SEARCH_PARAM_VALUES,
    ...PAGE_SEARCH_PARAM_VALUES,
    ...SORT_SEARCH_PARAM_VALUES,
  ],
};
const FILTER_LIST_SEARCH_PARAM: SearchParam = {
  q: FILTER_SEARCH_PARAM_VALUES,
};
const STATE: State = {
  filterState: { project: ["project 01", "project 02"] },
  paginationState: { pageIndex: 0, pageSize: 10 },
  sortState: [{ id: "updatedAt", desc: false }],
};

jest.mock("../views/GridsView/hooks/useFetchGrids/useFetchGrids", () => ({
  useFetchGrids: jest.fn(),
}));
jest.mock("../views/GridsView/hooks/useFetchFilters/useFetchFilters", () => ({
  useFetchFilters: jest.fn(),
}));

describe("Grid View Connect", () => {
  beforeEach(() => {
    (useFetchGrids as jest.Mock).mockReturnValue("mockGridList");
    (useFetchFilters as jest.Mock).mockReturnValue("mockFiltersList");
  });
  afterEach(() => {
    jest.clearAllMocks();
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <StateContext.Provider value={STATE}>{children}</StateContext.Provider>
  );
  it("should fetch grid and filter list with search params", () => {
    const { result } = renderHook(() => useConnect(), { wrapper });
    // Verify that useFetchGrids was called with the correct parameters.
    expect(useFetchGrids).toHaveBeenCalledWith(GRID_LIST_SEARCH_PARAM);
    // Verify that useFetchFilters was called with the correct parameters.
    expect(useFetchFilters).toHaveBeenCalledWith(FILTER_LIST_SEARCH_PARAM);
    // Verify the returned values from useConnect.
    expect(result.current.gridList).toBe("mockGridList");
    expect(result.current.filtersList).toBe("mockFiltersList");
  });
});
describe("Grid View Connect Utilities", () => {
  it("should generate correct filter search params from state", () => {
    expect(getFilterSearchParamValue(STATE)).toEqual(
      FILTER_SEARCH_PARAM_VALUES,
    );
    expect(buildFilterListSearchParam(STATE)).toEqual(FILTER_LIST_SEARCH_PARAM);
  });
  it("should generate correct grid list search params from state", () => {
    expect(getPaginationSearchParamValue(STATE)).toEqual(
      PAGE_SEARCH_PARAM_VALUES,
    );
    expect(getSortSearchParamValue(STATE)).toEqual(SORT_SEARCH_PARAM_VALUES);
    expect(buildGridListSearchParam(STATE)).toEqual(GRID_LIST_SEARCH_PARAM);
  });
});
