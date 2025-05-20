import { API, DJANGO_URL, MOCKED_APIS, MOCKED_POST_APIS, POST_API } from '../constants/api';

export async function fetchResource(requestURL: string): Promise<Response> {
  const mockResponse = MOCKED_APIS[new URL(requestURL).pathname as API];
  if (mockResponse !== undefined) {
    return Promise.resolve({
      status: 200,
      json: async () => {
        return typeof mockResponse === 'function' ? mockResponse(requestURL) : mockResponse;
      },
    }) as Promise<Response>;
  }

  const response = await fetch(requestURL, {
    credentials: 'include', // Include cookies in the request
  });

  // Check if the response status is 302 (redirect) or if the URL includes the login page
  if (response.status === 302 || response.url.includes('/admin/login')) {
    window.location.href = `${DJANGO_URL}/admin/login`;
    return Promise.reject(new Error('User is not authenticated, redirecting to login.'));
  }

  return response;
}

export async function postResource(requestURL: string, body: Record<string, unknown>): Promise<Response> {
  const mockResponse = MOCKED_POST_APIS[new URL(requestURL).pathname as POST_API];
  if (mockResponse !== undefined) {
    return Promise.resolve({
      status: 200,
      json: async () => {
        return typeof mockResponse === 'function' ? mockResponse(requestURL) : mockResponse;
      },
    }) as Promise<Response>;
  }

  const response = await fetch(requestURL, {
    method: 'POST',
    credentials: 'include', // Include cookies in the request
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  // Check if the response status is 302 (redirect) or if the URL includes the login page
  if (response.status === 302 || response.url.includes('/admin/login')) {
    window.location.href = `${DJANGO_URL}/admin/login`;
    return Promise.reject(new Error('User is not authenticated, redirecting to login.'));
  }

  return response;
}
