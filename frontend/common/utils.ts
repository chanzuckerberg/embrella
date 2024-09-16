// /**
//  * Fetch request.
//  * @param requestURL - Request URL.
//  * @returns promise (response).
//  */
// export async function fetchResource(requestURL: string): Promise<Response> {
//   return await fetch(requestURL, {
//     credentials: 'include',  // Include cookies in the request
//   });
// }

/**
 * Fetch request.
 * @param requestURL - Request URL.
 * @returns promise (response).
 */
export async function fetchResource(requestURL: string): Promise<Response> {
  const response = await fetch(requestURL, {
    credentials: "include", // Include cookies in the request
  });

  // Check if the response status is 302 (redirect) or if the URL includes the login page
  if (response.status === 302 || response.url.includes("/admin/login")) {
    // Detect the current host, protocol, and port dynamically
    const currentHost = window.location.hostname;
    const currentPort = window.location.port ? `:${window.location.port}` : ""; // Include port if available
    const currentProtocol = window.location.protocol;

    // Construct the login URL dynamically based on the detected host, protocol, and port
    // if you want to test locally, change the currentPort to :8000
    const loginURL = `${currentProtocol}//${currentHost}${currentPort}/admin/login`;

    // Redirect to the dynamically generated login page
    window.location.href = loginURL;
    return Promise.reject(
      new Error("User is not authenticated, redirecting to login."),
    );
  }

  return response;
}



/**
 * Returns the request URL.
 * @param base - Base URL.
 * @param url - URL (relative reference to the base URL).
 * @param searchParams - Search parameters.
 * @returns request URL.
 */
export function getRequestURL(
  base: string,
  url = "/",
  searchParams?: SearchParam[],
): string {
  const requestURL = new URL(url, base);
  for (const searchParam of searchParams || []) {
    requestURL.searchParams.set(
      searchParam.name,
      JSON.stringify(searchParam.value),
    );
  }
  return requestURL.href;
}