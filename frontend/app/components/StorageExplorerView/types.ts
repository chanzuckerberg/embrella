import { FilterConfig } from '@app/common/types/filter';

/**
 * A recorded preservation judgement, or the absence of one.
 *
 * `mixed` is presentation-only: the backend never stores it, it means a parent's
 * descendants disagree. Nothing here deletes anything — `delete` records that a
 * human thinks a directory looks reclaimable.
 */
export type StorageStatus = 'unset' | 'preserve' | 'delete' | 'review' | 'mixed';

/**
 * One leaf of the storage tree: a run directory, or the session root when files
 * sit directly under the session folder.
 */
export interface StorageRunRow {
  /** Namespaced by the API (`"storagerun-1841"`) so it can't collide with a session row. */
  id: string;
  /** `id` is null when no ProcRun record matches the directory on disk. */
  run: { id: number | null; name: string };
  software: string;
  procRunId: number | null;
  directoryCount: number;
  fileCount: number;
  totalSizeBytes: number;
  totalSizeDisplay: string;
  lastModified: string | null;
  /** Absolute directory this leaf covers; the drill-down key. */
  pathPrefix: string;
  status: StorageStatus;
  /** Equal to `pathPrefix` if the decision is this row's, shorter if inherited, null if none. */
  decidedAtPrefix: string | null;
}

export interface StorageSessionData {
  /** Keyed on the session *name*, so unregistered sessions stay distinct rows. */
  storageSession: { id: string; name: string };
  sessionName: string;
  /** False when the directory name matches no MsiSession. */
  registered: boolean;
  msiSessionId: number | null;
  user: { id: number; username: string; fullName: string } | null;
  project: { id: number; name: string } | null;
  /** Filesystem owner, which may differ from the session's user. */
  fsOwner: string;
  cluster: string;
  softwareCount: number;
  runCount: number;
  directoryCount: number;
  fileCount: number;
  totalSizeBytes: number;
  totalSizeDisplay: string;
  lastModified: string | null;
  status: StorageStatus;
  runs: StorageRunRow[];
}

/**
 * The middle tier, derived client-side from a session's flat `runs`.
 */
export interface StorageSoftwareGroup {
  id: string;
  software: string;
  runCount: number;
  directoryCount: number;
  fileCount: number;
  totalSizeBytes: number;
  totalSizeDisplay: string;
  lastModified: string | null;
  status: StorageStatus;
  runs: StorageRunRow[];
}

/** Which snapshot the figures came from, from the list endpoint's `survey` block. */
export interface StorageSurvey {
  id: number;
  cluster: string;
  completedAt: string | null;
  /** The survey changed after its tree was built, so the figures may be behind. */
  stale: boolean;
}

/** One tile on the stats card. */
export interface StorageSizeBlock {
  totalSizeBytes: number;
  totalSizeDisplay: string;
  directoryCount: number;
  fileCount: number;
}

export interface StorageSummary {
  survey: StorageSurvey | null;
  total: StorageSizeBlock | null;
  inTree:
    | (StorageSizeBlock & {
        sessionCount: number;
        unregisteredSessionCount: number;
        runCount: number;
      })
    | null;
  /** Everything the software allowlist excludes — relion, warptools, and so on. */
  outsideTree: StorageSizeBlock | null;
  bySoftware: (StorageSizeBlock & { software: string; sessionCount: number })[];
}

export enum StorageFilterId {
  OWNER = 'OWNER',
  PROCESSING_SOFTWARE = 'PROCESSING_SOFTWARE',
  PROJECT = 'PROJECT',
  USER = 'USER',
}

export type StorageFilterCategory = 'owner' | 'processingSoftware' | 'project' | 'search' | 'user';

export type StorageFilterConfig = FilterConfig<StorageFilterId, StorageFilterCategory>;
