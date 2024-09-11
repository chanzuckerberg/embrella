import { act, renderHook } from "@testing-library/react";
import { delay, initFetch } from "@/testing/utils";
import { useFetchGrids } from "@/views/GridsView/hooks/useFetchGrids";
import { GRIDS } from "@/testing/constants";

beforeAll(() => {
  initFetch();
});

describe("useFetchData", () => {
  it("updates with successfully-fetched grids", async () => {
    const { result } = renderHook(() => useFetchGrids());
    expect(result.current).toBeUndefined();
    await act(async () => await delay());
    expect(result.current).toEqual(GRIDS);
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
});
