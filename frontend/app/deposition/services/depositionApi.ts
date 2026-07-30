/** Typed fetch helpers for the deposition API. */

import { API, DJANGO_URL } from '@app/common/constants/api';
import { deleteResource, fetchResource, patchResource, postResource } from '@app/common/queries/fetchResource';

import type {
  Dataset,
  Deposition,
  DepositionMethodLink,
  DepositionSession,
  Institution,
  Person,
  SubmissionList,
} from '../types';

/** Writable Person fields. `institution_id` sets the affiliation by Institution id. */
export interface PersonUpdate {
  given_name?: string;
  family_name?: string;
  orcid?: string | null;
  institution_id?: number | null;
}

const url = (path: string): string => `${DJANGO_URL}${path}`;

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = '';
    try {
      detail = JSON.stringify(await response.json());
    } catch {
      /* no body */
    }
    throw new Error(`Request failed: ${response.status} ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function createPerson(data: Partial<Person>): Promise<Person> {
  return parse(await postResource(url(API.PEOPLE), data as Record<string, unknown>));
}

export async function updatePerson(id: number, data: PersonUpdate): Promise<Person> {
  return parse(await patchResource(url(`${API.PEOPLE}${id}/`), data as Record<string, unknown>));
}

export async function searchPeople(term: string): Promise<Person[]> {
  const data = await parse<Person[] | { results: Person[] }>(
    await fetchResource(url(`${API.PEOPLE}?search=${encodeURIComponent(term)}`))
  );
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function searchInstitutions(term: string): Promise<Institution[]> {
  const data = await parse<Institution[] | { results: Institution[] }>(
    await fetchResource(url(`${API.INSTITUTIONS}?search=${encodeURIComponent(term)}`))
  );
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function createInstitution(name: string): Promise<Institution> {
  return parse(await postResource(url(API.INSTITUTIONS), { name }));
}

export async function fetchPeopleByIds(ids: number[]): Promise<Person[]> {
  if (ids.length === 0) return [];
  return parse(await fetchResource(url(`${API.PEOPLE}by-ids?ids=${ids.join(',')}`)));
}

export async function fetchSubmissions(scope?: 'mine'): Promise<SubmissionList> {
  const query = scope ? `?scope=${scope}` : '';
  return parse(await fetchResource(url(`${API.DEPOSITIONS}${query}`)));
}

export async function fetchDeposition(id: number): Promise<Deposition> {
  return parse(await fetchResource(url(`${API.DEPOSITIONS}${id}/`)));
}

export async function createDeposition(data: Partial<Deposition>): Promise<Deposition> {
  return parse(await postResource(url(API.DEPOSITIONS), data as Record<string, unknown>));
}

export async function updateDeposition(id: number, data: Partial<Deposition>): Promise<Deposition> {
  return parse(await patchResource(url(`${API.DEPOSITIONS}${id}/`), data));
}

export async function deleteDeposition(id: number): Promise<void> {
  return parse(await deleteResource(url(`${API.DEPOSITIONS}${id}/`)));
}

export async function createDataset(data: Partial<Dataset>): Promise<Dataset> {
  return parse(await postResource(url(API.DEPOSITION_DATASETS), data as Record<string, unknown>));
}

export async function fetchDataset(id: number): Promise<Dataset> {
  return parse(await fetchResource(url(`${API.DEPOSITION_DATASETS}${id}/`)));
}

export async function updateDataset(id: number, data: Partial<Dataset>): Promise<Dataset> {
  return parse(await patchResource(url(`${API.DEPOSITION_DATASETS}${id}/`), data));
}

export async function deleteDataset(id: number): Promise<void> {
  return parse(await deleteResource(url(`${API.DEPOSITION_DATASETS}${id}/`)));
}

export async function submitDataset(id: number): Promise<unknown> {
  return parse(await postResource(url(`${API.DEPOSITION_DATASETS}${id}/submit/`), {}));
}

export async function fetchDatasetJobStatus(id: number): Promise<unknown> {
  return parse(await fetchResource(url(`${API.DEPOSITION_DATASETS}${id}/job-status/`)));
}

export async function fetchSession(id: number): Promise<DepositionSession> {
  return parse(await fetchResource(url(`${API.DEPOSITION_SESSIONS}${id}/`)));
}

export async function updateSession(id: number, data: Partial<DepositionSession>): Promise<DepositionSession> {
  return parse(await patchResource(url(`${API.DEPOSITION_SESSIONS}${id}/`), data));
}

export async function autoFillSession(id: number): Promise<unknown> {
  return parse(await postResource(url(`${API.DEPOSITION_SESSIONS}${id}/auto-fill/`), {}));
}

export async function createMethodLink(data: Partial<DepositionMethodLink>): Promise<DepositionMethodLink> {
  return parse(await postResource(url(API.DEPOSITION_METHOD_LINKS), data as Record<string, unknown>));
}

export async function updateMethodLink(id: number, data: Partial<DepositionMethodLink>): Promise<DepositionMethodLink> {
  return parse(await patchResource(url(`${API.DEPOSITION_METHOD_LINKS}${id}/`), data));
}

export async function deleteMethodLink(id: number): Promise<void> {
  return parse(await deleteResource(url(`${API.DEPOSITION_METHOD_LINKS}${id}/`)));
}
