import { act, renderHook } from "@testing-library/react";
import { delay, initFetch } from "@/testing/utils";
import { useFetchFilters } from "@/views/GridsView/hooks/useFetchFilters";
import { FETCH_RESPONSE_FILTERS_LIST } from "@/testing/constants";

beforeAll(() => {
  initFetch();
});

describe("useFetchData", () => {
  it("updates with successfully-fetched grids", async () => {
    const { result } = renderHook(() => useFetchFilters());
    expect(result.current).toBeUndefined();
    await act(async () => await delay());
    expect(result.current).toEqual(FETCH_RESPONSE_FILTERS_LIST);
  });
});
