import { expect, Locator } from '@playwright/test';

import { API } from '@app/common/constants/api';
import { ROUTES } from '@app/common/constants/constants';
import { TEST_IDS } from '@app/common/constants/testIds';

import { PageObject } from './PageObject';

const ATTRIBUTE = { SORT: 'aria-sort' };
const BUTTON = 'button';
const FILTER_OPTION_PRIMARY_TEXT = '.primary-text';
// A sortable column header carries aria-sort ("none" until sorted, then "ascending"/"descending").
const SORTABLE_HEADER_SELECTOR = 'th[aria-sort]';
const SORTED_DIRECTION_REGEX = /ascending|descending/;
const MUI_TABLE_SORT_LABEL = '.MuiTableSortLabel-root';
const MUI_AUTOCOMPLETE_OPTION = '.MuiAutocomplete-option';
const MUI_CHIP_ROOT = '.MuiChip-root';
const MUI_POPPER_ROOT = '.MuiPopper-root';
const MUI_SELECTED_CLASS_REGEX = /Mui-selected/;
const MUI_SVG_ICON_ROOT = '.MuiSvgIcon-root';
const TABLE_BODY_ROW_SELECTOR = 'tbody tr';
const TABLE_HEAD = 'th';
const TOOLTIP = 'tooltip';

export class EntityTablePage extends PageObject {
  public async navigateToCryoGrids() {
    await this.page.goto(ROUTES.CRYO_GRIDS);
    await this.page.waitForURL(ROUTES.CRYO_GRIDS, {
      waitUntil: 'networkidle',
    });
  }

  public getTableLocator(): Locator {
    return this.page.getByTestId(TEST_IDS.ENTITY_TABLE);
  }

  public async noDataAvailable(): Promise<boolean> {
    const table = this.getTableLocator();
    if (!table) {
      return true;
    }

    const numRows = await table.locator(TABLE_BODY_ROW_SELECTOR).count();
    return numRows === 0;
  }

  public async noFiltersAvailable(): Promise<boolean> {
    const filters = this.getFilterButtonLocators();
    return await filters.nth(0).isDisabled();
  }

  // #region Locators
  public getPaginationLocator() {
    return this.page.getByTestId(TEST_IDS.ENTITY_TABLE_PAGINATION);
  }

  public getTableHeaderLocators(): Locator {
    return this.getTableLocator().locator(TABLE_HEAD);
  }

  public getTableHeaderLocator(nth: number): Locator {
    return this.getTableHeaderLocators().nth(nth);
  }

  public getTableSortIconLocator(): Locator {
    return this.getTableHeaderLocators().locator(MUI_SVG_ICON_ROOT);
  }

  public getDateHeaderLocator(): Locator {
    return this.getTableLocator().locator(SORTABLE_HEADER_SELECTOR);
  }

  public async getDateHeaderDirection(): Promise<string | null> {
    return await this.getDateHeaderLocator().getAttribute(ATTRIBUTE.SORT);
  }

  public getDateHeaderSortIconLocator(): Locator {
    return this.getDateHeaderLocator().locator(MUI_SVG_ICON_ROOT);
  }

  public getSideBarFilters(): Locator {
    return this.page.getByTestId(TEST_IDS.SIDEBAR_FILTERS);
  }

  public getFilterButtonLocators(): Locator {
    return this.getSideBarFilters().locator(BUTTON);
  }

  public getFilterPopperLocator(): Locator {
    return this.page.locator(MUI_POPPER_ROOT).and(this.page.getByRole(TOOLTIP));
  }

  public getFilterOptionLocators(): Locator {
    return this.getFilterPopperLocator().locator(MUI_AUTOCOMPLETE_OPTION);
  }

  public getFirstFilterOptionLocator(): Locator {
    return this.getFilterOptionLocators().nth(0);
  }

  public getFilterChipLocators(filter: Locator): Locator {
    return filter.locator('..').locator(MUI_CHIP_ROOT);
  }

  public getFirstFilterChip(): Locator {
    const filter = this.getFilterButtonLocators().nth(0);
    return this.getFilterChipLocators(filter);
  }
  // #region Locators

  // #region Text
  public async getFirstFilterOptionText(): Promise<string> {
    return await this.getFirstFilterOptionLocator().locator(FILTER_OPTION_PRIMARY_TEXT).innerText();
  }
  // #endregion Text

  // #region Click actions
  public async clickDateHeader(): Promise<void> {
    await this.getDateHeaderLocator().locator(MUI_TABLE_SORT_LABEL).click();
  }

  public async clickFirstFilter(): Promise<void> {
    await this.getFilterButtonLocators().nth(0).click();
  }

  public async clickFirstFilterOption(): Promise<void> {
    await this.getFirstFilterOptionLocator().click();
  }

  public async closeFilterPopper(): Promise<void> {
    // SDS ComplexFilter's popper dismisses on an outside click (not Escape).
    await this.page.mouse.click(5, 5);
  }

  public async clickFirstFilterChip(): Promise<void> {
    await this.getFirstFilterChip().click();
  }
  // #endregion Click actions

  // #region UI inputs
  public async toggleDateSort() {
    await Promise.all([
      this.clickDateHeader(),
      this.page.waitForResponse((response) => response.url().includes(`${API.GRIDS}?`) && response.status() === 200),
    ]);
  }

  public async applyFirstFilterOption() {
    await Promise.all([
      this.clickFirstFilterOption(),
      this.page.waitForResponse(
        (response) => response.url().includes(API.GRIDS_FILTERS_LIST) && response.status() === 200
      ),
    ]);
  }

  public async removeFirstFilterChip() {
    await Promise.all([
      this.clickFirstFilterChip(),
      this.page.waitForResponse(
        (response) => response.url().includes(API.GRIDS_FILTERS_LIST) && response.status() === 200
      ),
    ]);
  }
  // #endregion UI inputs

  // #region Verifications
  public async verifyPaginationPresence() {
    const [response] = await Promise.all([
      this.page.waitForResponse((response) => response.url().includes(`${API.GRIDS}?`) && response.status() === 200),
      this.page.reload(),
    ]);

    const {
      pagination: { totalPages },
    } = await response.json();

    // the backend paginates with orphans=3, so use totalPages
    const paginationElement = this.getPaginationLocator();
    if (totalPages > 1) {
      await expect(paginationElement).toBeVisible();
    } else {
      await expect(paginationElement).not.toBeVisible();
    }
  }

  public async verifySortableDateHeader() {
    const header = this.getDateHeaderLocator();
    await expect(header).toHaveCount(1);
    await expect(header).toHaveAttribute(ATTRIBUTE.SORT, SORTED_DIRECTION_REGEX);
  }

  public async verifySortIconVisible() {
    const sortIcon = this.getDateHeaderSortIconLocator();
    await expect(sortIcon).toBeVisible();
  }

  public async verifyColumnNotSortable(nth: number) {
    const header = this.getTableHeaderLocator(nth);
    // Non-sortable columns carry no aria-sort attribute at all.
    await expect(header).not.toHaveAttribute(ATTRIBUTE.SORT, SORTED_DIRECTION_REGEX);
    await header.click();
    await expect(header).not.toHaveAttribute(ATTRIBUTE.SORT, SORTED_DIRECTION_REGEX);
  }

  public async verifyFilterPopperVisible() {
    const popper = this.getFilterPopperLocator();
    await expect(popper).toBeVisible();
  }

  public async verifyFilterPopperClosed() {
    const popper = this.getFilterPopperLocator();

    await this.closeFilterPopper();
    await expect(popper).not.toBeVisible();
  }

  public async verifyFilterOptionsVisible() {
    const options = this.getFirstFilterOptionLocator();
    await expect(options).toBeVisible();
  }

  public async verifyFirstFilterOptionSelected() {
    const option = this.getFirstFilterOptionLocator();
    await expect(option).toHaveClass(MUI_SELECTED_CLASS_REGEX);
  }

  public async verifyFirstFilterOptionNotSelected() {
    const option = this.getFirstFilterOptionLocator();
    await expect(option).not.toHaveClass(MUI_SELECTED_CLASS_REGEX);
  }

  public async verifyNumFiltersSelected(expectedFiltersCount: number) {
    const chips = this.getFirstFilterChip();
    await expect(chips).toHaveCount(expectedFiltersCount);
  }

  public async verifyFirstFilterChipValue(value: string) {
    const firstChip = this.getFirstFilterChip();
    expect(await firstChip.innerText()).toEqual(value);
  }
  // #endregion Verifications
}
