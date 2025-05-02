import configs from "@configs/local";

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
    window.location.href = `${configs.API_URL}/admin/login`;
    return Promise.reject(
      new Error("User is not authenticated, redirecting to login."),
    );
  }

  return response;
}
