import { API, DJANGO_URL } from '@app/common/constants/api';
import {
  deleteResource,
  fetchResource,
  patchResource,
  postFormData,
  postResource,
} from '@app/common/queries/fetchResource';

import type { ScanResult } from '../components/annotations/scan';
import type {
  CopickRunOption,
  Dataset,
  Deposition,
  DepositionSession,
  Institution,
  Person,
  SubmissionList,
  SubmitResponse,
} from '../types';

export interface PersonUpdate {
  given_name?: string;
  family_name?: string;
  orcid?: string | null;
  institution_id?: number | null;
}

const url = (path: string): string => `${DJANGO_URL}${path}`;

export interface ApiError extends Error {
  status?: number;
  sshSetupRequired?: boolean;
  clusterId?: string;
}

export function isSshSetupRequired(e: unknown): e is ApiError & { clusterId: string } {
  return !!e && typeof e === 'object' && (e as ApiError).sshSetupRequired === true;
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = '';
    let body: Record<string, unknown> = {};
    try {
      body = (await response.json()) as Record<string, unknown>;
      message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body);
    } catch {
      /* no body */
    }
    const error = new Error(message || `Something went wrong (${response.status}). Please try again.`) as ApiError;
    error.status = response.status;
    if (response.status === 403 && body.ssh_setup_required) {
      error.sshSetupRequired = true;
      error.clusterId = typeof body.cluster_id === 'string' ? body.cluster_id : '';
    }
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function checkSshSetup(clusterId: string): Promise<{ username: string }> {
  const data = await parse<{ username?: string }>(
    await postResource(url(API.SSH_CHECK_SETUP), { cluster_id: clusterId })
  );
  return { username: typeof data.username === 'string' ? data.username : '' };
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

export async function submitDataset(id: number): Promise<SubmitResponse> {
  return parse(await postResource(url(`${API.DEPOSITION_DATASETS}${id}/submit/`), {}));
}

export async function pushDataset(id: number): Promise<SubmitResponse> {
  return parse(await postResource(url(`${API.DEPOSITION_DATASETS}${id}/push/`), {}));
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

export interface AnnotatedCount {
  count: number;
  scanned: boolean;
}

export async function getCopickRunObjects(sessionName: string, run: string): Promise<string[]> {
  const q = `?session_id=${encodeURIComponent(sessionName)}&run=${encodeURIComponent(run)}`;
  const data = await parse<{ objects?: string[] }>(await fetchResource(url(`${API.COPICK_RUN_OBJECTS}${q}`)));
  return data.objects ?? [];
}

/* Annotated-tomogram count for a session's selected copick configs, from the cached scan.json. */
export async function getAnnotatedCount(sessionName: string, runs: string[]): Promise<AnnotatedCount> {
  if (runs.length === 0) return { count: 0, scanned: true };
  const q = `?session_id=${encodeURIComponent(sessionName)}&runs=${encodeURIComponent(runs.join(','))}`;
  const data = await parse<{ annotated_count?: number; scanned?: boolean }>(
    await fetchResource(url(`${API.COPICK_ANNOTATED_COUNT}${q}`))
  );
  return { count: data.annotated_count ?? 0, scanned: data.scanned ?? false };
}

export interface CopickAretomoCompat {
  compatible: boolean;
  incompatible_runs: string[]; // annotated runs not produced by the deposited AreTomo run
  aretomo_runs: string[]; // full produced-run set, used to filter each annotation's runs
  scanned: boolean;
}

export async function fetchCopickAretomoCompat(
  sessionName: string,
  aretomoRun: string,
  copickRuns: string[]
): Promise<CopickAretomoCompat> {
  const run = aretomoRun.startsWith('run') ? aretomoRun : `run${aretomoRun}`;
  const q =
    `?session_name=${encodeURIComponent(sessionName)}` +
    `&run_number=${encodeURIComponent(run)}` +
    `&copick_runs=${encodeURIComponent(copickRuns.join(','))}`;
  const data = await parse<Partial<CopickAretomoCompat>>(await fetchResource(url(`${API.COPICK_ARETOMO_COMPAT}${q}`)));
  return {
    compatible: data.compatible ?? true,
    incompatible_runs: data.incompatible_runs ?? [],
    aretomo_runs: data.aretomo_runs ?? [],
    scanned: data.scanned ?? false,
  };
}

/* Read the cached scan.json for each selected run and merge its picks/segmentations/meshes. */
export async function scanCopickAnnotations(sessionName: string, runs: string[]): Promise<ScanResult> {
  const merged: ScanResult = { scanned: true, pending: false, picks: [], segmentations: [], meshes: [] };
  for (const run of runs) {
    const path = `${API.COPICK_PROJECT_DETAIL}${encodeURIComponent(sessionName)}/${encodeURIComponent(run)}/?scan=true`;
    const res = await fetchResource(url(path));
    if (!res.ok) {
      merged.scanned = false;
      continue;
    }
    const data = (await res.json()) as { project?: { annotations?: ScanResult } };
    const ann = data.project?.annotations ?? {};
    if (!ann.scanned) merged.scanned = false;
    // A pending marker (job running/triggered) is distinct from a missing file (never scanned).
    if (ann.pending) merged.pending = true;
    if (ann.error && !merged.error) merged.error = ann.error;
    // Sum in-flight progress across the configs still scanning.
    if (typeof ann.progress_total === 'number') {
      merged.progress_total = (merged.progress_total ?? 0) + ann.progress_total;
      merged.progress_done = (merged.progress_done ?? 0) + (ann.progress_done ?? 0);
    }
    merged.picks!.push(...(ann.picks ?? []));
    merged.segmentations!.push(...(ann.segmentations ?? []));
    merged.meshes!.push(...(ann.meshes ?? []));
  }
  return merged;
}

export async function rescanCopick(sessionName: string, runs: string[]): Promise<void> {
  const results = await Promise.allSettled(
    runs.map(async (run) => {
      const res = await postResource(
        url(`${API.COPICK_PROJECT_DETAIL}${encodeURIComponent(sessionName)}/${encodeURIComponent(run)}/scan/`),
        {}
      );
      if (!res.ok) throw new Error(`Copick scan could not be started for ${run} (${res.status})`);
    })
  );
  if (results.length > 0 && results.every((r) => r.status === 'rejected')) {
    throw new Error('Copick scan could not be started.');
  }
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
