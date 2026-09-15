import { DJANGO_URL } from '@app/common/constants/api';
import { fetchResource, postResource } from '@app/common/queries/fetchResource';

import { TEM_API } from '../constants';
import type { FormOptions, GridOption, MagnificationOption, UserOption } from '../types';

const url = (path: string): string => `${DJANGO_URL}${path}`;

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return (await response.json()) as T;
}

export async function fetchFormOptions(): Promise<FormOptions> {
  return parse<FormOptions>(await fetchResource(url(TEM_API.FORM_OPTIONS)));
}

export async function fetchUsers(): Promise<UserOption[]> {
  const data = await parse<{ users?: UserOption[]; results?: UserOption[] } | UserOption[]>(
    await fetchResource(url(TEM_API.USERS))
  );
  if (Array.isArray(data)) return data;
  return data.users ?? data.results ?? [];
}

/** Grids a user may pick from; all grids when no user filter is set. */
export async function fetchGrids(userId: number | null): Promise<GridOption[]> {
  const query = userId ? `?user_id=${userId}` : '';
  return parse<GridOption[]>(await fetchResource(url(`${TEM_API.GRIDS_BY_USER}${query}`)));
}

export async function fetchMagnifications(sessionPlanId: number): Promise<MagnificationOption[]> {
  return parse<MagnificationOption[]>(
    await fetchResource(url(`${TEM_API.MAGNIFICATIONS}?session_plan_id=${sessionPlanId}`))
  );
}

/** The server's suggested name, prefixed per plan when one is given (e.g. s26jun08a). */
export async function fetchSuggestedName(sessionPlanId: number | null): Promise<string> {
  const query = sessionPlanId ? `?session_plan_id=${sessionPlanId}` : '';
  const data = await parse<{ suggested_name: string }>(await fetchResource(url(`${TEM_API.SUGGEST_NAME}${query}`)));
  return data.suggested_name;
}

export interface CreateSessionPayload {
  name: string;
  session_plan_id: number | null;
  project_id: number | null;
  grid_id: number | null;
  magnification_id?: number;
  super_resolution?: boolean;
}

/** Field errors come back as `{ field: [messages] }`, so the raw response is returned for the caller to read. */
export function createSession(payload: CreateSessionPayload): Promise<Response> {
  return postResource(url(TEM_API.CREATE_SESSION), payload as unknown as Record<string, unknown>);
}
