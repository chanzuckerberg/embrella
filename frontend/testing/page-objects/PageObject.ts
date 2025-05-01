import test, { Page } from '@playwright/test';

export abstract class PageObject {
  public page: Page;
  public baseUrl: string;

  constructor(page: Page) {
    this.page = page;
    this.baseUrl = test.info().project.use.baseURL as string;
  }

  public async pause(seconds: number) {
    await this.page.waitForTimeout(seconds * 1000);
  }

  public async reload() {
    await this.page.reload();
  }
}
