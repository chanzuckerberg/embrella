import { act, renderHook } from "@testing-library/react";
import { delay, initFetch } from "../testing/utils";
import { useFetchGrids } from "../hooks/useFetchGrids";
import { GRID_A } from "../testing/constants";

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
