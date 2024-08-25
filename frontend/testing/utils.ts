import { FETCH_RESPONSES } from "./constants";
import { TestResponse } from "./entities";

export function initFetch(
  getBlocker: () => Promise<void> | undefined = () => undefined,
): void {
  global.fetch = jest.fn(async (url): Promise<TestResponse> => {
    await getBlocker();
    url = url.toString();
    const responseInfo =
      Object.hasOwn(FETCH_RESPONSES, url) && FETCH_RESPONSES[url];
    if (!responseInfo) throw new TypeError("Failed to fetch");
    return {
      status: responseInfo.status ?? 200,
      text: async () => responseInfo.body ?? "",
      json: async () => JSON.parse(responseInfo.body ?? ""),
    };
  }) as unknown as typeof fetch;
}

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

export function delay(ms = 5): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function getLastFetchResult(): Promise<TestResponse | undefined> {
  const fetchMock = fetch as unknown as jest.Mock<Promise<TestResponse>>;
  return fetchMock.mock.results[fetchMock.mock.results.length - 1].value;
}
