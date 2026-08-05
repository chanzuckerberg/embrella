import { DJANGO_URL } from '../constants/api';

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function redirectIfUnauthenticated(response: Response): void {
  if (response.status === 401 || response.status === 302 || response.url?.includes('/accounts/login')) {
    window.location.href = `${DJANGO_URL}/accounts/login/?next=${encodeURI(window.location.href)}`;
    throw new Error('Authentication required');
  }
}

/** Shared core for state-changing requests: attaches CSRF token + credentials. */
async function mutateResource(
  method: 'POST' | 'PATCH' | 'DELETE',
  requestURL: string,
  body?: Record<string, unknown>
): Promise<Response> {
  const csrfToken = getCsrfToken();
  const response = await fetch(requestURL, {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(csrfToken && { 'X-CSRFToken': csrfToken }),
    },
    ...(body !== undefined && { body: JSON.stringify(body) }),
  });

  redirectIfUnauthenticated(response);
  return response;
}

export async function fetchResource(requestURL: string): Promise<Response> {
  const response = await fetch(requestURL, {
    credentials: 'include', // Include cookies in the request
  });

  redirectIfUnauthenticated(response);
  return response;
}

export function postResource(requestURL: string, body: Record<string, unknown>): Promise<Response> {
  return mutateResource('POST', requestURL, body);
}
/** Like postResource, but for multipart bodies. */
export async function postFormData(requestURL: string, body: FormData): Promise<Response> {
  const csrfToken = getCsrfToken();
  const response = await fetch(requestURL, {
    method: 'POST',
    credentials: 'include',
    headers: {
      ...(csrfToken && { 'X-CSRFToken': csrfToken }),
    },
    body,
  });

  redirectIfUnauthenticated(response);
  return response;
}

export function patchResource(requestURL: string, body: Record<string, unknown>): Promise<Response> {
  return mutateResource('PATCH', requestURL, body);
}

export function deleteResource(requestURL: string, body?: Record<string, unknown>): Promise<Response> {
  return mutateResource('DELETE', requestURL, body);
}
