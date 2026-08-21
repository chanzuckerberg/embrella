import { FilterConfig } from '@app/common/types/filter';

/**
 * One processing run, as nested under a session row by
 * `GET /tem/v1/session-overview/`.
 */
export interface SessionRunRow {
  /** Namespaced by the API (`"run-311"`) so run ids can't collide with session ids. */
  id: string;
  run: { id: number; name: string };
  planName: string;
  planLabel: string;
  createdAt: string;
}

export interface SessionOverviewData {
  session: { id: number; name: string };
  sessionDate: string;
  /** The user who created the tem session record */
  user: { id: number; username: string; fullName: string } | null;
  project: { id: number; name: string } | null;
  scope: string;
  workflow: string;
  grid: { id: number; name: string } | null;
  runCount: number;
  /** Distinct plan labels across the session's runs, already sorted. */
  processingSoftware: string[];
  reviewCount: number;
  lastRunAt: string | null;
  runs: SessionRunRow[];
}

/**
 * The middle tier of the table showing processing software grouped by plan label
 */
export interface SessionSoftwareGroup {
  id: string;
  planLabel: string;
  /** Distinct machine keys behind this label; usually one. */
  planNames: string[];
  runCount: number;
  latestRunAt: string | null;
  runs: SessionRunRow[];
}

export enum SessionFilterId {
  PROCESSING_SOFTWARE = 'PROCESSING_SOFTWARE',
  PROJECT = 'PROJECT',
  SCOPE = 'SCOPE',
  USER = 'USER',
  WORKFLOW = 'WORKFLOW',
}

export type SessionFilterCategory = 'processingSoftware' | 'project' | 'scope' | 'search' | 'user' | 'workflow';

export type SessionFilterConfig = FilterConfig<SessionFilterId, SessionFilterCategory>;
