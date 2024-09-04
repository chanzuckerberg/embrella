import { act, renderHook } from "@testing-library/react";
import { delay, getLastFetchResult, initFetch } from "@/testing/utils";
import { useFetchData } from "@/hooks/useFetchData/useFetchData";
import { URL_FOO, URL_NONEXISTENT } from "@/testing/constants";

beforeAll(() => {
  initFetch();
});

describe("useFetchData", () => {
  it("does not change when data fails to fetch", async () => {
    const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
    const { result } = renderHook(() => useFetchData(URL_NONEXISTENT));
    expect(result.current).toEqual({ isSuccess: false });
    await act(async () => await delay());
    expect(await getLastFetchResult()).toHaveProperty("status", 404);
    expect(result.current).toEqual({ isSuccess: false });
    consoleErrorSpy.mockRestore();
  });

  it("updates with successfully-fetched data", async () => {
    const { result } = renderHook(() => useFetchData(URL_FOO));
    expect(result.current).toEqual({ isSuccess: false });
    await act(async () => await delay());
    expect(await getLastFetchResult()).toHaveProperty("status", 200);
    expect(result.current).toEqual({ data: "foo", isSuccess: true });
  });

  it("doesn't update until shouldFetch is true", async () => {
    expect(fetch).toHaveBeenCalledTimes(2);
    const { rerender, result } = renderHook(
      ({ shouldFetch, url }) => useFetchData(url, shouldFetch),
      {
        initialProps: {
          shouldFetch: false,
          url: URL_FOO,
        },
      },
    );
    expect(result.current).toEqual({ isSuccess: false });
    await act(async () => await delay());
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(result.current).toEqual({ isSuccess: false });
    rerender({
      shouldFetch: true,
      url: URL_FOO,
    });
    await act(async () => await delay());
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(await getLastFetchResult()).toHaveProperty("status", 200);
    expect(result.current).toEqual({ data: "foo", isSuccess: true });
  });
});
