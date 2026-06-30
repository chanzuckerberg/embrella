import { expect, Locator, test } from '@playwright/test';

import { GRID_COLUMN_DEFS } from '@app/components/GridsView/constants/columns';
import { GRID_FILTER_CONFIGS } from '@app/components/GridsView/constants/filters';

import { EntityTablePage } from '@testing/page-objects/EntityTablePage';

const { describe } = test;

const DESCRIPTION = 'Skip the test; BE is unavailable';

let gridsPage: EntityTablePage;

let filters: Locator;

test.beforeEach(async ({ page }) => {
  gridsPage = new EntityTablePage(page);
  await gridsPage.navigateToCryoGrids();
});

test.afterEach(async () => {
  await gridsPage.reload();
});

describe('Grids', () => {
  describe('grid list', () => {
    test('displays grid list', async () => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
    });
  });

  describe('grid list columns', () => {
    let noDataAvailable = false;
    test.beforeEach(async () => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
      noDataAvailable = await gridsPage.noDataAvailable();
    });

    test('displays configured headers with header label', async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      const tableHeaders = gridsPage.getTableHeaderLocators();

      await expect(tableHeaders).toHaveCount(GRID_COLUMN_DEFS.length);

      for (let i = 0; i < GRID_COLUMN_DEFS.length; i++) {
        const headerLabel = GRID_COLUMN_DEFS[i].header as string;
        await expect(tableHeaders.nth(i)).toContainText(headerLabel);
      }
    });
  });

  describe('grid list pagination', () => {
    let noDataAvailable = false;

    test.beforeEach(async () => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
      noDataAvailable = await gridsPage.noDataAvailable();
    });

    test(`should display pagination only when grid list rows is greater than max rows per page`, async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      await gridsPage.verifyPaginationPresence();
    });
  });

  describe('grid list sorting', () => {
    let noDataAvailable = false;

    test.beforeEach(async () => {
      await expect(gridsPage.getTableLocator()).toBeVisible();
      noDataAvailable = await gridsPage.noDataAvailable();
    });

    test('displays sortable headers', async () => {
      test.skip(noDataAvailable, DESCRIPTION);
      const sortableColumnDef = GRID_COLUMN_DEFS.filter(({ enableSorting }) => enableSorting);
      const sortIcons = gridsPage.getTableSortIconLocator();
      await expect(sortIcons).toHaveCount(sortableColumnDef.length);
    });

    test('displays a sorted header with sort icon', async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      // The grid list isn't sorted on load, so sort it first.
      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();

      await gridsPage.verifySortIconVisible();
    });

    test('sorted header changes sort direction when header is clicked', async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();

      const direction01 = await gridsPage.getDateHeaderDirection();

      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();

      const direction02 = await gridsPage.getDateHeaderDirection();
      expect(direction01).not.toEqual(direction02);
    });

    test('sort order should be toggled, but not turned "off", after each toggle', async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();
      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();
      await gridsPage.toggleDateSort();
      await gridsPage.verifySortableDateHeader();
    });

    test('header should not sort when sorting is not enabled', async () => {
      test.skip(noDataAvailable, DESCRIPTION);

      for (let i = 0; i < GRID_COLUMN_DEFS.length; i++) {
        if (GRID_COLUMN_DEFS[i].enableSorting) {
          continue;
        }

        await gridsPage.verifyColumnNotSortable(i);
        break;
      }
    });
  });

  describe('grid filters', () => {
    let noFiltersAvailable = false;
    test.beforeEach(async () => {
      filters = gridsPage.getFilterButtonLocators();
      noFiltersAvailable = await gridsPage.noFiltersAvailable();
    });

    test('displays filters', async () => {
      await expect(gridsPage.getSideBarFilters()).toBeVisible();
    });

    test('should display configured filters with correct filter label', async () => {
      const FILTERS = GRID_FILTER_CONFIGS.flat();

      await expect(filters).toHaveCount(FILTERS.length);

      for (let i = 0; i < FILTERS.length; i++) {
        await expect(filters.nth(i)).toContainText(FILTERS[i].label);
      }
    });

    test('should open filter popper when filter is clicked', async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();
      await gridsPage.verifyFilterPopperVisible();
    });

    test('should close filter popper when clicking away', async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();
      await gridsPage.verifyFilterPopperVisible();
      await gridsPage.verifyFilterPopperClosed();
    });

    test('should display filter options', async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();
      await gridsPage.verifyFilterOptionsVisible();
    });

    test('should keep the filter popper open after selecting a filter item', async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();
      await gridsPage.clickFirstFilterOption();
      await gridsPage.verifyFilterPopperVisible();
    });

    test('should apply filter', async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();

      const filterOptionValue = await gridsPage.getFirstFilterOptionText();

      await gridsPage.applyFirstFilterOption();
      await gridsPage.verifyFirstFilterOptionSelected();
      await gridsPage.closeFilterPopper();
      await gridsPage.verifyNumFiltersSelected(1);
      await gridsPage.verifyFirstFilterChipValue(filterOptionValue);
    });

    test('should clear applied filter after selecting filter chip', async () => {
      test.skip(noFiltersAvailable, DESCRIPTION);

      await gridsPage.clickFirstFilter();
      await gridsPage.applyFirstFilterOption();
      await gridsPage.closeFilterPopper();

      const filterChip = gridsPage.getFirstFilterChip();

      await gridsPage.removeFirstFilterChip();
      await expect(filterChip).not.toBeVisible();
      await gridsPage.clickFirstFilter();
      await gridsPage.verifyFirstFilterOptionNotSelected();
    });
  });
});
