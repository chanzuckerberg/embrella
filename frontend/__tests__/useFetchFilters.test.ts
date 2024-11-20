import { act, renderHook } from "@testing-library/react";
import { delay, initFetch } from "@/testing/utils";
import { useFetchGridsFilters } from "@/views/GridsView/hooks/useFetchGridsFilters/useFetchGridsFilters";
import { FETCH_RESPONSE_FILTERS_LIST } from "@/testing/constants";

beforeAll(() => {
  initFetch();
});

describe("useFetchData", () => {
  it("updates with successfully-fetched filter list", async () => {
    const { result } = renderHook(() => useFetchGridsFilters({}));
    expect(result.current).toBeUndefined();
    await act(async () => await delay());
    expect(result.current).toEqual(FETCH_RESPONSE_FILTERS_LIST);
  });
});
