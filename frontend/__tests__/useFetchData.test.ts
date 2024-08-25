import { renderHook } from "@testing-library/react";
import { initFetch } from "../testing/utils";
import { useFetchData } from "@/hooks/useFetchData";

const fetchBlock = new Promise<void>(() => undefined);

beforeAll(() => {
  initFetch(() => fetchBlock);
});

describe("useFetchData", () => {
  it("", () => {
    const { result } = renderHook(() =>
      useFetchData("https://localhost:8000/foo"),
    );
    expect(result.current).toEqual({ isSuccess: false });
  });
});
