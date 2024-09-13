import { expect, test } from "@playwright/test";

const { describe } = test;

describe("Grids list", () => {
  test("check that the grids list is displayed", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("grids")).toBeVisible();
  });
});
