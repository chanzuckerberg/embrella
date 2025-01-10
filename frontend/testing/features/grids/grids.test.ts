import { expect, Locator, Page, Response, test } from "@playwright/test";

import { API } from "@app/common/constants/api";
// import { ROUTES } from "@app/common/constants/constants";
import { TEST_IDS } from "@app/common/constants/testIds";
import { EntityList } from "@app/common/types/tableState";

import { GRID_COLUMN_DEFS } from "@app/components/GridsView/constants/columns";
import { GRID_FILTER_CONFIGS } from "@app/components/GridsView/constants/filters";

import {
  ATTRIBUTE,
  BUTTON,
  KEYBOARD_KEY,
  MUI_AUTOCOMPLETE_OPTION,
  MUI_CHIP_ROOT,
  MUI_POPPER_ROOT,
  // MUI_SVG_ICON_ROOT,
  // TABLE_BODY_ROW,
  // TH,
  TOOLTIP,
} from "@testing/features/common/constants";
import { EntityTablePage } from "@testing/page-objects/EntityTablePage";
import { verify } from "crypto";

const { describe } = test;

// const COLUMN_CONFIGS = GRID_COLUMN_DEFS;
const DESCRIPTION = "Skip the test; BE is unavailable";
const FILTER_CONFIGS = GRID_FILTER_CONFIGS;
const FILTER_OPTION_PRIMARY_TEXT = ".primary-text";
// const HEADER_WITH_DIRECTION_ATTRIBUTE = "th[direction]";

let gridsPage: EntityTablePage;

let filters: Locator;

test.beforeEach(async ({ page }) => {
  // await goToGridList(page);
  gridsPage = new EntityTablePage(page);
  await gridsPage.navigateToCryoGrids();
});

test.afterEach(async () => {
  await gridsPage.reload();
});

describe("Grids", () => {
  describe("grid list", () => {
    test("displays grid list", async ({ page }) => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
    });
  });

  describe("grid list columns", () => {
    let noDataAvailable = false;
    test.beforeEach(async () => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
      noDataAvailable = await gridsPage.noDataAvailable();
    });

    test("displays configured headers with header label", async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      const tableHeaders = gridsPage.getTableHeaderLocators();

      await expect(tableHeaders).toHaveCount(GRID_COLUMN_DEFS.length);

      for (let i = 0; i < GRID_COLUMN_DEFS.length; i++) {
        const headerLabel = GRID_COLUMN_DEFS[i].header as string;
        await expect(tableHeaders.nth(i)).toContainText(headerLabel);
      }
    });
  });

  describe("grid list pagination", () => {
    let noDataAvailable = false;

    test.beforeEach(async () => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
      noDataAvailable = await gridsPage.noDataAvailable();
    });

    test(`should display pagination only when grid list rows is greater than max rows per page`, async ({
      page,
    }) => {
      test.skip(noDataAvailable, DESCRIPTION);

      await gridsPage.verifyPaginationPresence();
      // const {
      //   pagination: { pageSize, totalResults },
      // } = await waitForResponse<EntityList>(page, API.GRIDS, () =>
      //   page.reload(),
      // );
      // const pagination = gridsPage.getPaginationLocator();
      // if (pageSize < totalResults) {
      //   await expect(pagination).toBeVisible();
      // } else {
      //   await expect(pagination).not.toBeVisible();
      // }
    });
  });

  describe("grid list sorting", () => {
    let noDataAvailable = false;

    test.beforeEach(async () => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
      noDataAvailable = await gridsPage.noDataAvailable();
    });

    test("displays sortable headers", async () => {
      test.skip(noDataAvailable, DESCRIPTION);
      const sortableColumnDef = GRID_COLUMN_DEFS.filter(
        ({ enableSorting }) => enableSorting,
      );
      const sortIcons = gridsPage.getTableSortIconLocator();
      await expect(sortIcons).toHaveCount(sortableColumnDef.length);
    });

    test("displays a sorted header with sort icon", async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      await gridsPage.verifySortableDateHeader();

      await gridsPage.verifySortIconVisible();
    });

    test("sorted header changes sort direction when header is clicked", async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      await gridsPage.verifySortableDateHeader();

      const direction01 = gridsPage.getDateHeaderDirection();

      // await gridsPage.clickDateHeader();
      // await waitForRequest(page, header, API.GRIDS);

      await gridsPage.toggleDateSort();

      // await expect(header).toHaveAttribute(ATTRIBUTE.DIRECTION);
      await gridsPage.verifySortableDateHeader();

      const direction02 = await gridsPage.getDateHeaderDirection();
      expect(direction01).not.toEqual(direction02);
    });

    test('sort order should be toggled, but not turned "off", after each toggle', async () => {
      test.skip(noDataAvailable, DESCRIPTION);
      // const header = table.locator(HEADER_WITH_DIRECTION_ATTRIBUTE);
      // for (let i = 0; i < 3; i++) {
      //   await expect(header).toHaveAttribute(ATTRIBUTE.DIRECTION);
      //   await waitForRequest(page, header, API.GRIDS);
      // }
      await gridsPage.verifySortableDateHeader();
      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();
      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();
      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();
    });

    test("header should not sort when sorting is not enabled", async () => {
      test.skip(noDataAvailable, DESCRIPTION);
      for (let i = 0; i < GRID_COLUMN_DEFS.length; i++) {
        if (GRID_COLUMN_DEFS[i].enableSorting) {
          continue;
        }
        // const header = getTableHeaderLocator(table, i);
        // await expect(header).not.toHaveAttribute(ATTRIBUTE.DIRECTION);
        // await header.click();
        // await expect(header).not.toHaveAttribute(ATTRIBUTE.DIRECTION);
        await gridsPage.verifyColumnNotSortable(i);
        break;
      }
    });
  });

  describe("grid filters", () => {
    let noFiltersAvailable = false;
    test.beforeEach(async () => {
      filters = gridsPage.getFilterButtonLocators();
      noFiltersAvailable = await gridsPage.noFiltersAvailable();
    });

    test("displays filters", async () => {
      await expect(gridsPage.getSideBarFilters()).toBeVisible();
    });

    test("should display configured filters with correct filter label", async () => {
      const FILTERS = GRID_FILTER_CONFIGS.flat();
      // Verify the number of filters displayed.
      await expect(filters).toHaveCount(FILTERS.length);
      // Verify the filter name.
      for (let i = 0; i < FILTERS.length; i++) {
        await expect(filters.nth(i)).toContainText(FILTERS[i].label);
      }
    });

    test("should open filter popper when filter is clicked", async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();
      await gridsPage.verifyFilterPopperVisible();
    });

    test("should close filter popper with escape key", async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);
      await gridsPage.clickFirstFilter();
      await gridsPage.verifyFilterPopperVisible();
      await gridsPage.verifyFilterPopperClosed();
    });

    test("should display filter options", async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);
      await gridsPage.clickFirstFilter();
      await gridsPage.verifyFilterOptionsVisible();
      // const filterOptions = getFilterOptionLocators(page).nth(0);
      // await expect(filterOptions).toBeVisible();
    });

    test("should keep the filter popper open after selecting a filter item", async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);
      await gridsPage.clickFirstFilter();
      await gridsPage.clickFirstFilterOption();
      await gridsPage.verifyFilterPopperVisible();
      // const filterPopper = getFilterPopperLocator(page);
      // await getFilterOptionLocators(page).nth(0).click();
      // await expect(filterPopper).toBeVisible();
    });

    test("should apply filter", async ({ page }) => {
      test.skip(noFiltersAvailable, DESCRIPTION);
      await gridsPage.clickFirstFilter();
      // const filter = filters.nth(0);
      // await filter.click();

      const filterOptionValue = await gridsPage.getFirstFilterOptionText();
      // const filterOption = getFilterOptionLocator(page);
      // const filterOptionValue = await filterOption
      //   .locator(FILTER_OPTION_PRIMARY_TEXT)
      //   .innerText();

      await gridsPage.applyFirstFilterOption();
      // await waitForRequest(page, filterOption, API.GRIDS_FILTERS_LIST);

      gridsPage.verifyFirstFilterOptionSelected();
      // await expect(filterOption).toHaveClass(/Mui-selected/);

      await gridsPage.closeFilterPopper();
      // await page.keyboard.press(KEYBOARD_KEY.ESCAPE);

      await gridsPage.verifyNumFiltersSelected(1);
      // Verify the number of filter chips displayed.
      // const filterChips = getFilterChipLocators(filter);
      // await expect(filterChips).toHaveCount(1);

      await gridsPage.verifyFirstFilterChipValue(filterOptionValue);
      // Verify the filter chip value is equal to the filter option value.
      // const filterChip = filterChips.nth(0);
      // const filterChipValue = await filterChip.innerText();
      // expect(filterChipValue).toEqual(filterOptionValue);
    });

    test("should clear applied filter after selecting filter chip", async ({
      page,
    }) => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();
      // const filter = filters.nth(0);
      // await filter.click();

      await gridsPage.applyFirstFilterOption();
      // Apply filter.
      // await waitForRequest(
      //   page,
      //   getFilterOptionLocators(page).nth(0),
      //   API.GRIDS_FILTERS_LIST,
      // );

      await gridsPage.closeFilterPopper();
      // await page.keyboard.press(KEYBOARD_KEY.ESCAPE);

      const filterChip = gridsPage.getFirstFilterChip();
      // const filterChip = getFilterChipLocators(filter).nth(0);

      await gridsPage.removeFirstFilterChip();
      // Clear filter.
      // await waitForRequest(page, filterChip, API.GRIDS_FILTERS_LIST);

      // Verify the filter chip is no longer visible.
      await expect(filterChip).not.toBeVisible();

      // Verify filter option is no longer selected.
      await gridsPage.clickFirstFilter();
      gridsPage.verifyFirstFilterOptionNotSelected();
    });
  });
});

// function getFilterChipLocators(filter: Locator): Locator {
//   return filter.locator("..").locator(MUI_CHIP_ROOT);
// }

// function getFilterLocators(page: Page): Locator {
//   return page.getByTestId(TEST_IDS.SIDEBAR_FILTERS).locator(BUTTON);
// }

// function getFilterOptionLocator(page: Page, nth = 0): Locator {
//   return getFilterOptionLocators(page).nth(nth);
// }

// function getFilterOptionLocators(page: Page): Locator {
//   return getFilterPopperLocator(page).locator(MUI_AUTOCOMPLETE_OPTION);
// }

// function getFilterPopperLocator(page: Page): Locator {
//   return page.locator(MUI_POPPER_ROOT).and(page.getByRole(TOOLTIP));
// }

// function getPaginationLocator(page: Page) {
//   return page.getByTestId(TEST_IDS.ENTITY_TABLE_PAGINATION);
// }

// function getTableLocator(page: Page): Locator {
//   return page.getByTestId(TEST_IDS.ENTITY_TABLE);
// }

// function getTableHeaderLocator(table: Locator, nth: number): Locator {
//   return getTableHeaderLocators(table).nth(nth);
// }

// function getTableHeaderLocators(table: Locator): Locator {
//   return table.locator(TH);
// }

// function getTableSortIconLocator(table: Locator): Locator {
//   return getTableHeaderLocators(table).locator(MUI_SVG_ICON_ROOT);
// }

// async function goToGridList(page: Page): Promise<void> {
//   await page.goto(ROUTES.CRYO_GRIDS);
// }

// async function openFilter(filters: Locator) {
//   const filter = filters.nth(0);
//   await filter.click();
// }

// async function shouldSkipGridTest(table?: Locator): Promise<boolean> {
//   if (!table) return true;
//   return (await table.locator(TABLE_BODY_ROW).count()) === 0;
// }

// async function shouldSkipFilterTest(filter?: Locator): Promise<boolean> {
//   if (!filter) return true;
//   return await filter.isDisabled();
// }

// async function waitForRequest(
//   page: Page,
//   locator: Locator,
//   requestURL: string,
// ): Promise<void> {
//   await Promise.all([
//     page.waitForResponse(
//       (response) =>
//         response.url().includes(requestURL) && response.status() === 200,
//     ),
//     locator.click(),
//   ]);
// }

// async function waitForResponse<R>(
//   page: Page,
//   requestURL: string,
//   onRequest: () => Promise<Response | null>,
// ): Promise<R> {
//   const [response] = await Promise.all([
//     page.waitForResponse(
//       (response) =>
//         response.url().includes(requestURL) && response.status() === 200,
//     ),
//     onRequest(),
//   ]);
//   return await response.json();
// }
