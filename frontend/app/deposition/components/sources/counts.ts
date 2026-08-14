import type { TomogramSubsetMode } from '../../types';
import type { SourceRow } from './types';

export function subsetCount(row: SourceRow): number | undefined {
  const sel = row.subset_selection;
  if (Array.isArray(sel)) return sel.length; // CSV → one entry per row
  if (sel && typeof sel === 'object') {
    const positions = (sel as Record<string, unknown>)['Selected positions'];
    if (Array.isArray(positions)) return positions.length;
  }
  return undefined;
}

export function rowSelected(row: SourceRow, mode: TomogramSubsetMode): number | undefined {
  if (row.tomogram_total == null) return undefined;
  if (mode === 'all') return row.tomogram_total;
  if (mode === 'annotated') return row.tomogram_selected;
  if (row.subset_csv_path) return undefined;
  const n = subsetCount(row);
  if (n == null) return 0; // no subset uploaded yet
  return Math.min(n, row.tomogram_total);
}

export interface SourcesRollup {
  sessions: number;
  totalTomograms: number;
  selectedTomograms: number;
  droppedTomograms: number;
  selectedKnown: boolean;
  annotatedTomograms: number;
  copickConfigs: number;
  denoisedSessions: number;
}

export function rollup(rows: SourceRow[], mode: TomogramSubsetMode): SourcesRollup {
  const acc: SourcesRollup = {
    sessions: 0,
    totalTomograms: 0,
    selectedTomograms: 0,
    droppedTomograms: 0,
    selectedKnown: true,
    annotatedTomograms: 0,
    copickConfigs: 0,
    denoisedSessions: 0,
  };
  for (const r of rows) {
    if (r.msi_session_name) acc.sessions += 1;
    if (r.denoise_run_name) acc.denoisedSessions += 1;
    acc.copickConfigs += r.selected_copick_runs.length;
    if (r.tomogram_total != null) {
      acc.totalTomograms += r.tomogram_total;
      acc.annotatedTomograms += r.tomogram_selected ?? 0;
      const sel = rowSelected(r, mode);
      if (sel == null) acc.selectedKnown = false;
      else acc.selectedTomograms += sel;
    }
  }
  acc.droppedTomograms = Math.max(0, acc.totalTomograms - acc.selectedTomograms);
  return acc;
}
