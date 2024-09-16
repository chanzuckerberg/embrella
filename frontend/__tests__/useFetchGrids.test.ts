import { act, renderHook } from "@testing-library/react";
import { delay, initFetch } from "@/testing/utils";
import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids";
import {
  GRID_B,
  GRIDS,
  TEST_DEFAULT_GRIDS_PAGE_SIZE,
} from "@/testing/constants";

beforeAll(() => {
  initFetch();
});

describe("useFetchData", () => {
  it("updates with successfully-fetched grids", async () => {
    const { result } = renderHook(() => useFetchGrids());
    expect(result.current).toBeUndefined();
    await act(async () => await delay());
    expect(result.current).toBeDefined();
    if (!result.current) return;
    expect(result.current.grids).toEqual(GRIDS);
    expect(result.current.pagination).toEqual({
      page: 1,
      pageSize: TEST_DEFAULT_GRIDS_PAGE_SIZE,
      totalPages: 1,
      totalResults: GRIDS.length,
    });
  });

  it("gets sorted grids", async () => {
    const { result: resultAsc } = renderHook(() =>
      useFetchGrids({ sort: { ascending: true, column: "cassette" } }),
    );
    await act(async () => await delay());
    const gridsAsc = resultAsc.current?.grids;
    expect(gridsAsc).toBeDefined();

    const { result: resultDesc } = renderHook(() =>
      useFetchGrids({ sort: { ascending: false, column: "cassette" } }),
    );
    await act(async () => await delay());
    const gridsDesc = resultDesc.current?.grids;
    expect(gridsDesc).toBeDefined();

    if (gridsAsc && gridsDesc)
      expect(gridsAsc[0]).toEqual(gridsDesc[gridsDesc.length - 1]);
  });

  it("handles pagination", async () => {
    const { result } = renderHook(() =>
      useFetchGrids({ pagination: { page: 2, pageSize: 1 } }),
    );
    expect(result.current).toBeUndefined();
    await act(async () => await delay());
    expect(result.current).toBeDefined();
    if (!result.current) return;
    expect(result.current.grids).toEqual([GRID_B]);
    expect(result.current.pagination).toEqual({
      page: 2,
      pageSize: 1,
      totalPages: GRIDS.length,
      totalResults: GRIDS.length,
    });
  });
});
