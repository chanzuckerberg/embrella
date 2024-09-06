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
    credentials: 'include',  // Include cookies in the request
  });

  // Check if the response status is 302 (redirect)
  if (response.status === 302 || response.url.includes('/admin/login')) {
    // Hard-code the redirect to the login page
    const loginURL = 'http://localhost:8000/admin/login';
    console.log('Redirecting to login page:', loginURL);
    window.location.href = loginURL; // Redirect to the login page
    return Promise.reject(new Error('User is not authenticated, redirecting to login.'));
  }

  return response;
}


