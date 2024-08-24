import { fetchResource } from "../common/utils";
import { GRID_A } from "../testing/constants";

describe("fetchResource", () => {
  it("returns fetch response", async () => {
    const response = await fetchResource(
      "http://localhost:8000/cryo_grids/v1/grids",
    );
    expect((await response.json()).Results[0]).toEqual(GRID_A);
  });
});
