import { act, renderHook } from "@testing-library/react";
import { delay, initFetch } from "@testing/utils";
import { FETCH_RESPONSE_FILTERS_LIST } from "@testing/constants";
import { useFetchFilters } from "./useFetchFilters";
import { API } from "../../constants/api";

beforeAll(() => {
  initFetch();
});

describe("useFetchData", () => {
  it("updates with successfully-fetched filter list", async () => {
    const { result } = renderHook(() =>
      useFetchFilters(API.GRIDS_FILTERS_LIST, {}),
    );
    expect(result.current).toBeUndefined();
    await act(async () => await delay());
    expect(result.current).toEqual(FETCH_RESPONSE_FILTERS_LIST);
  });
});
