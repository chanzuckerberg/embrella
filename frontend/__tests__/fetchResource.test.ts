import { initFetch } from "@/testing/utils";
import { fetchResource, getRequestURL } from "@/common/utils";
import {
  GRID_A,
  URL_BASE,
  URL_GRIDS,
  URL_NONEXISTENT,
} from "@/testing/constants";
import { ApiListResponse, GridData } from "@/common/types";

beforeAll(() => {
  initFetch();
});

describe("fetchResource", () => {
  it("fails with error when invalid url is provided", async () => {
    const promise = fetchResource("http://invalidurl");
    await expect(promise).rejects.toThrow(TypeError);
  });

  it("returns error response", async () => {
    const response = await fetchResource(
      getRequestURL(URL_BASE, URL_NONEXISTENT),
    );
    expect(response.status).toEqual(404);
  });

  it("returns fetch response", async () => {
    const response = await fetchResource(getRequestURL(URL_BASE, URL_GRIDS));
    const responseData: ApiListResponse<GridData> = await response.json();
    expect(responseData.result[0]).toEqual(GRID_A);
  });
});
