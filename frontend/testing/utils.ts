import { FETCH_RESPONSES } from "./constants";

export function initFetch(
  getBlocker: () => Promise<void> | undefined = () => undefined,
): void {
  global.fetch = jest.fn(async (url) => {
    await getBlocker();
    url = url.toString();
    const responseInfo =
      Object.hasOwn(FETCH_RESPONSES, url) && FETCH_RESPONSES[url];
    if (!responseInfo) throw new TypeError("Failed to fetch");
    return {
      status: responseInfo.status,
      text: () => responseInfo.body ?? "",
      json: () => JSON.parse(responseInfo.body ?? ""),
    } as unknown as Response;
  });
}
