/**
 * Fetch request.
 * @param requestURL - Request URL.
 * @returns promise (response).
 */
export async function fetchResource(
  requestURL: string | URL,
): Promise<Response> {
  return await fetch(requestURL);
}
