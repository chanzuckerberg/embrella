import { TestResponse } from "@/testing/types";
import { FETCH_RESPONSES } from "@/testing/constants";
import { SearchParamValue } from "@/common/types";

/**
 * Initialize mock `fetch` function in global scope, since `fetch` is normally unavailable in tests.
 * @param getBlocker - Function returning a promise that the mock-fetch will await before returning.
 */
export function initFetch(
  getBlocker: () => Promise<void> | undefined = () => undefined,
): void {
  global.fetch = jest.fn(async (url): Promise<TestResponse> => {
    await getBlocker();
    const urlObj = new URL(url);
    const relativeURL = urlObj.pathname;
    const responseInfo =
      Object.hasOwn(FETCH_RESPONSES, relativeURL) &&
      FETCH_RESPONSES[relativeURL];
    if (!responseInfo) throw new TypeError("Failed to fetch");
    const body =
      typeof responseInfo.body === "function"
        ? responseInfo.body(urlObj)
        : responseInfo.body;
    return {
      status: responseInfo.status ?? 200,
      text: async () => body ?? "",
      json: async () => JSON.parse(body ?? ""),
      url: url.toString(),
    };
  }) as unknown as typeof fetch;
}

/**
 * Polyfill for Promise.withResolvers; returns a new promise, along with its "resolve" function and "reject" function.
 * @returns promise with resolvers.
 */
// Adapted from https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/withResolvers#description
export function promiseWithResolvers<T>(): [
  Promise<T>,
  (v: T) => void,
  (v: unknown) => void,
] {
  let resolve: (v: T) => void;
  let reject: (v: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return [promise, resolve!, reject!];
}

/**
 * Returns a promise that resolves after a given amount of time.
 * @param ms - Number of milliseconds to wait before resolving.
 * @returns promise.
 */
export function delay(ms = 5): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Get the resolved value of the most recent promise returned by the mock `fetch` function, or undefined if none exists.
 * @returns test response previously returned by `fetch`, or undefined.
 */
export function getLastFetchResult(): Promise<TestResponse | undefined> {
  const fetchMock = fetch as unknown as jest.Mock<Promise<TestResponse>>;
  return fetchMock.mock.results[fetchMock.mock.results.length - 1].value;
}

/**
 * Returns the first value of a search parameter category, or a default value if the category is not found.
 * @param values - Search parameter values.
 * @param category - Category.
 * @param index - Category values index.
 * @param defaultValue - Default value.
 * @returns search param category value.
 */
export function getSearchParamFirstValue<T extends boolean | number | string>(
  values: SearchParamValue[],
  category: string,
  index = 0,
  defaultValue?: T,
): T | undefined {
  const value = values.find((v) => v.category === category)?.value;
  if (!value) return defaultValue;
  return Array.isArray(value) ? value[index] : value || defaultValue;
}
