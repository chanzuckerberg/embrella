import { expect, Locator } from "@playwright/test";

import { ROUTES } from "@app/common/constants/constants";
import { TEST_IDS } from "@app/common/constants/testIds";

import { PageObject } from "./PageObject";
import { GRID_COLUMN_DEFS } from "@app/components/GridsView/constants/columns";
import { GRID_FILTER_CONFIGS } from "@app/components/GridsView/constants/filters";
import { API } from "@app/common/constants/api";

const ATTRIBUTE = { DIRECTION: "direction" };
const BUTTON = "button";
const GRID_COLUMN_CONFIGS = GRID_COLUMN_DEFS;
const DESCRIPTION = "Skip the test; BE is unavailable";
const FILTER_CONFIGS = GRID_FILTER_CONFIGS;
const FILTER_OPTION_PRIMARY_TEXT = ".primary-text";
const HEADER_WITH_DIRECTION_ATTRIBUTE = "th[direction]";
const KEYBOARD_KEY = {
  ESCAPE: "Escape",
};
const MUI_AUTOCOMPLETE_OPTION = ".MuiAutocomplete-option";
const MUI_CHIP_ROOT = ".MuiChip-root";
const MUI_POPPER_ROOT = ".MuiPopper-root";
const MUI_SVG_ICON_ROOT = ".MuiSvgIcon-root";
const TABLE_BODY_ROW_SELECTOR = "tbody tr";
const TABLE_HEAD = "th";

export class EntityTablePage extends PageObject {
  public async navigateToCryoGrids() {
    await this.page.goto(ROUTES.CRYO_GRIDS);
    await this.page.waitForURL(ROUTES.CRYO_GRIDS, {
      waitUntil: "networkidle",
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
    return this.getTableLocator().locator(HEADER_WITH_DIRECTION_ATTRIBUTE);
  }

  public async getDateHeaderDirection(): Promise<string | null> {
    return await this.getDateHeaderLocator().getAttribute(ATTRIBUTE.DIRECTION);
  }

  public getDateHeaderSortIconLocator() {
    return this.getDateHeaderLocator().locator(MUI_SVG_ICON_ROOT);
  }

  public async clickDateHeader() {
    await this.getDateHeaderLocator().click();
  }

  public getFilterLocators(): Locator {
    return page.getByTestId(TEST_IDS.SIDEBAR_FILTERS).locator(BUTTON);
  }

  public async toggleDateSort() {
    await Promise.all([
      this.clickDateHeader(),
      this.page.waitForResponse(
        (response) =>
          response.url().includes(API.GRIDS) && response.status() === 200,
      ),
    ]);
  }

  public async verifySortableDateHeader() {
    const header = this.getDateHeaderLocator();
    await expect(header).toHaveCount(1);
    await expect(header).toHaveAttribute(ATTRIBUTE.DIRECTION);
  }

  public async verifySortIconVisible() {
    const sortIcon = this.getDateHeaderSortIconLocator();
    await expect(sortIcon).toBeVisible();
  }

  public async verifyColumnNotSortable(nth: number) {
    const header = this.getTableHeaderLocator(nth);
    await expect(header).not.toHaveAttribute(ATTRIBUTE.DIRECTION);
    await header.click();
    await expect(header).not.toHaveAttribute(ATTRIBUTE.DIRECTION);
  }
}
