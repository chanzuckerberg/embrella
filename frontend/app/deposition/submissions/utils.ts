import { alpha, type Theme } from '@mui/material/styles';

import type { Dataset, Deposition } from '../types';
import type { ChipColor, SortKey } from './constants';

export function timeAgo(iso?: string): string {
  if (!iso) return '—';
  const min = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}d ago`;
  return `${Math.floor(day / 7)}w ago`;
}

export function absDate(iso?: string): string {
  return iso ? new Date(iso).toLocaleString() : '';
}


const ts = (d?: string): number => (d ? new Date(d).getTime() : 0);

export function compareDatasets(a: Dataset, b: Dataset, sort: SortKey): number {
  switch (sort) {
    case 'recent':
      return ts(b.updated_at) - ts(a.updated_at);
    case 'oldest':
      return ts(a.updated_at) - ts(b.updated_at);
    case 'dataset_id':
      return (a.dataset_id ?? 0) - (b.dataset_id ?? 0);
  }
}

export function datasetMatches(ds: Dataset, q: string): boolean {
  return (
    `ds-${ds.dataset_id ?? ''}`.toLowerCase().includes(q) ||
    (ds.title ?? '').toLowerCase().includes(q) ||
    (ds.type ?? '').toLowerCase().includes(q) ||
    (ds.session_names ?? []).some((n) => n.toLowerCase().includes(q))
  );
}

export function depositionMatches(dep: Deposition, q: string): boolean {
  return `cdp-${dep.deposition_id ?? ''}`.toLowerCase().includes(q) || (dep.title ?? '').toLowerCase().includes(q);
}

export function softChipSx(color: ChipColor) {
  return (theme: Theme) => {
    const paletteEntry =
      color === 'default'
        ? { main: theme.palette.grey[500], dark: theme.palette.grey[700] }
        : theme.palette[color];
    return {
      backgroundColor: alpha(paletteEntry.main, 0.14),
      color: paletteEntry.dark,
      borderColor: alpha(paletteEntry.main, 0.4),
      fontWeight: 500,
    };
  };
}
