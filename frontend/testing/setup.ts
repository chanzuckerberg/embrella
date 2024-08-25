import { FETCH_RESPONSES } from "./constants";

global.fetch = jest.fn(async (url) => {
  url = url.toString();
  const responseInfo =
    Object.hasOwn(FETCH_RESPONSES, url) && FETCH_RESPONSES[url];
  if (!responseInfo) throw new TypeError("Failed to fetch");
  return new Response(responseInfo.body, { status: responseInfo.status });
});
