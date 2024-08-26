import { act, renderHook, waitFor } from "@testing-library/react";
import { delay, getLastFetchResult, initFetch, promiseWithResolvers } from "../testing/utils";
import { useFetchData } from "@/hooks/useFetchData";
import { useFetchGrids } from "@/hooks/useFetchGrids";
import { GRID_A } from "@/testing/constants";

beforeAll(() => {
  initFetch();
});

describe("useFetchData", () => {
  it("updates with successfully-fetched grids", async () => {
    const { result } = renderHook(() =>
      useFetchGrids(),
    );
    expect(result.current).toBeUndefined();
    await act(async () => await delay());
    expect(result.current).toEqual([GRID_A]);
  });
});
