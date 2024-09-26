import { ROUTES } from "@/common/constants";
import { TEST_ID_GRIDS } from "@/views/GridsView/components/Main/components/GridList/common/constants";
import { expect, Locator, Page, test } from "@playwright/test";
import { TEST_ID_GRID_FILTERS } from "@/views/GridsView/components/Main/components/GridFilter/constants";
import { GRID_FILTER_CONFIGS } from "@/views/GridsView/components/Main/components/GridFilter/filters/filter";
import {
  BUTTON,
  KEYBOARD_KEY,
  MUI_AUTOCOMPLETE_OPTION,
  MUI_CHIP_ROOT,
  MUI_POPPER_ROOT,
  TOOLTIP,
} from "@/testing/features/common/constants";

const { describe } = test;

const FILTER_CONFIGS = GRID_FILTER_CONFIGS;
const FILTER_OPTION_PRIMARY_TEXT = ".primary-text";

describe("Grids", () => {
  describe("grid", () => {
    test("displays grid table", async ({ page }) => {
      await goToGridList(page);
      await expect(page.getByTestId(TEST_ID_GRIDS)).toBeVisible();
    });
  });
  describe("filters", () => {
    const FILTERS = FILTER_CONFIGS.flat();
    test("displays filters", async ({ page }) => {
      await goToGridList(page);
      await expect(page.getByTestId(TEST_ID_GRID_FILTERS)).toBeVisible();
    });
    test("should display configured filters with correct filter label", async ({
      page,
    }) => {
      await goToGridList(page);
      const filters = getFilterLocators(page);
      // Verify the number of filters displayed.
      await expect(filters).toHaveCount(FILTERS.length);
      // Verify the filter name.
      for (let i = 0; i < FILTERS.length; i++) {
        await expect(filters.nth(i)).toContainText(FILTERS[i].label);
      }
    });
    test("should open filter popper when filter is clicked", async ({
      page,
    }) => {
      await goToGridList(page);
      await openFilter(page);
      const filterPopper = getFilterPopperLocator(page);
      await expect(filterPopper).toBeVisible();
    });
    test("should close filter popper with escape key", async ({ page }) => {
      await goToGridList(page);
      await openFilter(page);
      const filterPopper = getFilterPopperLocator(page);
      await expect(filterPopper).toBeVisible();
      await page.keyboard.press(KEYBOARD_KEY.ESCAPE);
      await expect(filterPopper).not.toBeVisible();
    });
    test("should display filter options", async ({ page }) => {
      await goToGridList(page);
      await openFilter(page);
      const filterOptions = getFilterOptionLocators(page);
      await expect(filterOptions).toBeVisible();
    });
    test("should keep the filter popper open after selecting a filter item", async ({
      page,
    }) => {
      await goToGridList(page);
      await openFilter(page);
      const filterPopper = getFilterPopperLocator(page);
      await getFilterOptionLocators(page).nth(0).click();
      await expect(filterPopper).toBeVisible();
    });
    test("should apply filter", async ({ page }) => {
      await goToGridList(page);
      const filter = getFilterLocators(page).nth(0);
      await skipIfFilterDisabled(filter);
      await filter.click();
      const filterOption = getFilterOptionLocator(page);
      const filterOptionValue = await filterOption
        .locator(FILTER_OPTION_PRIMARY_TEXT)
        .innerText();
      await filterOption.click();
      // Verify filter option is selected.
      await expect(filterOption).toHaveClass(/Mui-selected/);
      await page.keyboard.press(KEYBOARD_KEY.ESCAPE);
      const filterChips = getFilterChipLocators(filter);
      // Verify the number of filter chips displayed.
      await expect(filterChips).toHaveCount(1);
      const filterChip = filterChips.nth(0);
      const filterChipValue = await filterChip.innerText();
      // Verify the filter chip value is equal to the filter option value.
      expect(filterChipValue).toEqual(filterOptionValue);
    });
    test("should clear applied filter after selecting filter chip", async ({
      page,
    }) => {
      await goToGridList(page);
      const filter = getFilterLocators(page).nth(0);
      await skipIfFilterDisabled(filter);
      await filter.click();
      await getFilterOptionLocators(page).nth(0).click();
      await page.keyboard.press(KEYBOARD_KEY.ESCAPE);
      const filterChip = getFilterChipLocators(filter).nth(0);
      // Clear filter.
      await filterChip.click();
      // Verify the filter chip is no longer visible.
      await expect(filterChip).not.toBeVisible();
      // Verify filter option is no longer selected.
      await filter.click();
      const filterOption = getFilterOptionLocator(page);
      await expect(filterOption).not.toHaveClass(/Mui-selected/);
    });
  });
});

function getFilterChipLocators(filter: Locator): Locator {
  return filter.locator("..").locator(MUI_CHIP_ROOT);
}

function getFilterLocators(page: Page): Locator {
  return page.getByTestId(TEST_ID_GRID_FILTERS).locator(BUTTON);
}

function getFilterOptionLocator(page: Page, nth = 0): Locator {
  return getFilterOptionLocators(page).nth(nth);
}

function getFilterOptionLocators(page: Page): Locator {
  return getFilterPopperLocator(page).locator(MUI_AUTOCOMPLETE_OPTION);
}

function getFilterPopperLocator(page: Page): Locator {
  return page.locator(MUI_POPPER_ROOT).and(page.getByRole(TOOLTIP));
}

async function goToGridList(page: Page): Promise<void> {
  await page.goto(ROUTES.HOME);
}

async function openFilter(page: Page) {
  const filter = getFilterLocators(page).nth(0);
  await skipIfFilterDisabled(filter);
  await filter.click();
}

async function skipIfFilterDisabled(filter: Locator) {
  // Skip the test if the filter is disabled; BE is unavailable.
  if (await filter.isDisabled()) {
    test.skip();
  }
}
