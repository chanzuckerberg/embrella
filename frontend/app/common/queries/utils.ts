/**
 * Returns the request URL.
 * @param base - Base URL.
 * @param url - URL (relative reference to the base URL).
 * @param searchParam - Search parameters.
 * @returns request URL.
 */
export function getRequestURL(
  base: string,
  url: string,
  searchParam: Record<string, unknown> = {},
): string {
  const requestURL = new URL(url, base);
  for (const [name, value] of Object.entries(searchParam)) {
    requestURL.searchParams.set(name, getRequestURLSearchParamValue(value));
  }
  return requestURL.href;
}

/**
 * Returns the search parameter value, stringify-ing objects.
 * @param value - Value.
 * @returns search parameter value.
 */
function getRequestURLSearchParamValue(value: unknown): string {
  return value && typeof value === "object"
    ? JSON.stringify(value)
    : String(value);
}
