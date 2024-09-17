import { TEST_ID_GRIDS } from "@/views/GridsView/components/GridList/common/constants";
import { expect, test } from "@playwright/test";

const { describe } = test;

describe("Grids", () => {
  test("displays grids", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId(TEST_ID_GRIDS)).toBeVisible();
  });
});
