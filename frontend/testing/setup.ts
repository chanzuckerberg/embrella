import { FETCH_RESPONSES } from "./constants";

global.fetch = jest.fn(async (url) => {
  url = url.toString();
  const responseInfo = Object.hasOwn(FETCH_RESPONSES, url)
    ? FETCH_RESPONSES[url]
    : {
        status: 404,
      };
  return new Response(responseInfo.body, { status: responseInfo.status });
});
