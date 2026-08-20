import { API, DJANGO_URL } from '@app/common/constants/api';
import {
  deleteResource,
  fetchResource,
  patchResource,
  postFormData,
  postResource,
} from '@app/common/queries/fetchResource';

import type {
  CopickRunOption,
  Dataset,
  Deposition,
  DepositionMethodLink,
  DepositionSession,
  Institution,
  Person,
  SubmissionList,
} from '../types';

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

/** Runs cryoetportalprep init on the cluster; returns the session with metadata populated. */
export async function autoFillSession(id: number): Promise<DepositionSession> {
  return parse(await postResource(url(`${API.DEPOSITION_SESSIONS}${id}/auto-fill/`), {}));
}

export async function listMsiSessions(): Promise<string[]> {
  const data = await parse<{ session_names?: string[] }>(await fetchResource(url(API.MSI_SESSIONS_LIST)));
  return data.session_names ?? [];
}

export async function getMsiSessionId(sessionName: string): Promise<number> {
  const q = encodeURIComponent(sessionName);
  const data = await parse<{ session_id: number }>(await fetchResource(url(`${API.MSI_SESSION_ID}?session_name=${q}`)));
  return data.session_id;
}

export async function listPlanRuns(planType: 'aretomo3' | 'denoiset', sessionName: string): Promise<string[]> {
  const q = `?plan_type=${planType}&session_name=${encodeURIComponent(sessionName)}`;
  const data = await parse<{ sessions?: { name: string; run_numbers?: string[] }[] }>(
    await fetchResource(url(`${API.PLAN_RUNS}${q}`))
  );
  return data.sessions?.[0]?.run_numbers ?? [];
}

export async function listCopickRuns(sessionName: string): Promise<CopickRunOption[]> {
  const q = `?session_id=${encodeURIComponent(sessionName)}`;
  const data = await parse<{ copick_runs?: CopickRunOption[] }>(await fetchResource(url(`${API.COPICK_RUNS}${q}`)));
  return data.copick_runs ?? [];
}

/* Annotated-tomogram count for a session's selected copick configs. Slow - SSH scan. */
export async function getAnnotatedCount(sessionName: string, runs: string[]): Promise<number> {
  if (runs.length === 0) return 0;
  const q = `?session_id=${encodeURIComponent(sessionName)}&runs=${encodeURIComponent(runs.join(','))}`;
  const data = await parse<{ annotated_count?: number }>(await fetchResource(url(`${API.COPICK_ANNOTATED_COUNT}${q}`)));
  return data.annotated_count ?? 0;
}

/* Total tomograms for a session + AreTomo run, from the metadata summary (num_tomograms). */
export async function getTomogramCount(sessionName: string, runNumber: string): Promise<number> {
  const run = runNumber.startsWith('run') ? runNumber : `run${runNumber}`;
  const q = `?session_name=${encodeURIComponent(sessionName)}&run_number=${encodeURIComponent(run)}`;
  const res = await fetchResource(url(`${API.METADATA_SUMMARY}${q}`));
  if (!res.ok) throw new Error(`tomogram count unavailable (${res.status})`);
  const text = (await res.text()).replace(/\bNaN\b/g, 'null');
  const data = text ? (JSON.parse(text) as { num_tomograms?: number }) : {};
  return data.num_tomograms ?? 0;
}

export async function uploadSubsetCsv(sessionId: number, file: File): Promise<{ subset_selection: unknown }> {
  const form = new FormData();
  form.append('file', file);
  return parse(await postFormData(url(`${API.DEPOSITION_SESSIONS}${sessionId}/subset-csv/`), form));
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
