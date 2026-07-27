import type { DatasetStatus } from '../types';

export type FilterKey = 'all' | DatasetStatus;

export const COLS = [
  { key: 'dataset', label: 'Dataset', width: '16%', align: 'left' as const },
  { key: 'sessions', label: 'Imaging Session(s)', width: '24%', align: 'left' as const },
  { key: 'type', label: 'Type', width: '20%', align: 'left' as const },
  { key: 'status', label: 'Status', width: '12%', align: 'left' as const },
  { key: 'updated', label: 'Updated', width: '12%', align: 'left' as const },
  { key: 'actions', label: 'Actions', width: '16%', align: 'right' as const },
];

export const MAX_SESSION_NAMES = 2;

export type ChipColor = 'default' | 'secondary' | 'info' | 'success' | 'warning' | 'error';

export const STATUS_META: Record<DatasetStatus, { label: string; color: ChipColor }> = {
  draft: { label: 'Draft', color: 'default' },
  syncing: { label: 'Syncing', color: 'warning' },
  pushed: { label: 'Pushed', color: 'success' },
  failed: { label: 'Failed', color: 'error' },
};

export const TYPE_META: Record<string, ChipColor> = {
  'Tomos only': 'secondary',
  Dataset: 'info',
  'Annotations only': 'warning',
};

export const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pushed', label: 'Pushed' },
  { key: 'syncing', label: 'In progress' },
  { key: 'draft', label: 'Drafts' },
  { key: 'failed', label: 'Failed' },
];

export type SortKey = 'recent' | 'oldest' | 'dataset_id';

export const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'recent', label: 'Recently updated' },
  { key: 'oldest', label: 'Oldest updated' },
  { key: 'dataset_id', label: 'Dataset ID' },
];
