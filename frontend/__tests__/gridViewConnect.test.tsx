import { useConnect } from "@/views/GridsView/components/Main/connect";
import { renderHook } from "@testing-library/react";
import { State } from "@/views/GridsView/common/store/types";
import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids/useFetchGrids";
import { useFetchFilters } from "@/views/GridsView/hooks/useFetchFilters/useFetchFilters";
import { StateContext } from "@/views/GridsView/common/store";
import React, { ReactNode } from "react";
import {
  buildFilterSearchParam,
  buildSearchParam,
} from "@/views/GridsView/components/Main/utils";

const MOCK_Q_PARAM = {
  q: [{ category: "project", value: ["project 01", "project 02"] }],
};
const MOCK_STATE: State = {
  filterState: { project: ["project 01", "project 02"] },
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
    <StateContext.Provider value={MOCK_STATE}>{children}</StateContext.Provider>
  );
  it("should generate qParam correctly and build search params", () => {
    const q = MOCK_Q_PARAM.q;
    const { result } = renderHook(() => useConnect(), { wrapper });
    // Verify that useFetchGrids was called with the correct parameters.
    expect(useFetchGrids).toHaveBeenCalledWith({}, { q });
    // Verify that useFetchFilters was called with the correct parameters.
    expect(useFetchFilters).toHaveBeenCalledWith({ q });
    // Verify the returned values from useConnect.
    expect(result.current.gridList).toBe("mockGridList");
    expect(result.current.filtersList).toBe("mockFiltersList");
  });
});
describe("Grid View Connect Utilities", () => {
  const filterState = MOCK_STATE.filterState;
  const qParam = MOCK_Q_PARAM;
  const q = qParam.q;
  it("should generate correct filter search params from filter state", () => {
    const searchParam = buildFilterSearchParam(filterState);
    expect(searchParam).toEqual(qParam);
  });
  it("should build correct search params", () => {
    const searchParam = buildSearchParam({ qParam });
    expect(searchParam).toEqual({ q });
  });
});
