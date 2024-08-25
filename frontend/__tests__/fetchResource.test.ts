import { initFetch } from "../testing/utils";
import { fetchResource } from "../common/utils";
import { GRID_A } from "../testing/constants";

beforeAll(() => {
  initFetch();
});

describe("fetchResource", () => {
  it("fails with error when invalid url is provided", async () => {
    const promise = fetchResource("http://invalidurl");
    await expect(promise).rejects.toThrow(TypeError);
  });

  it("returns error response", async () => {
    const response = await fetchResource("http://localhost:8000/nonexistent");
    expect(response.status).toEqual(404);
  });

  it("returns fetch response", async () => {
    const response = await fetchResource(
      "http://localhost:8000/cryo_grids/v1/grids",
    );
    expect((await response.json()).Results[0]).toEqual(GRID_A);
  });
});
