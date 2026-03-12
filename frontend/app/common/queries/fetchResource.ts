import { API, DJANGO_URL, MOCKED_APIS, MOCKED_POST_APIS, POST_API } from '../constants/api';

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

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

  // Check for authentication errors - redirect to login
  if (response.status === 401 || response.status === 302 || response.url.includes('/admin/login')) {
    window.location.href = `${DJANGO_URL}/admin/login/?next=${encodeURI(window.location.href)}`;
    return Promise.reject(new Error('Authentication required'));
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

  const csrfToken = getCsrfToken();
  const response = await fetch(requestURL, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken && { 'X-CSRFToken': csrfToken }),
    },
    body: JSON.stringify(body),
  });

  // Check for authentication errors - redirect to login
  if (response.status === 401 || response.status === 302 || response.url.includes('/admin/login')) {
    window.location.href = `${DJANGO_URL}/admin/login/?next=${encodeURI(window.location.href)}`;
    return Promise.reject(new Error('Authentication required'));
  }

  return response;
}

export const patchResource = async (url: string, body: object): Promise<Response> => {
  const csrfToken = getCsrfToken();
  return fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken && { 'X-CSRFToken': csrfToken }),
    },
    credentials: 'include',
    body: JSON.stringify(body),
  });
};
