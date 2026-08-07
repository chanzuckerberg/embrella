import type { TomogramSubsetMode } from '../../types';
import type { SourceRow } from './types';

export function rowSelected(row: SourceRow, mode: TomogramSubsetMode): number | undefined {
  if (row.tomogram_total == null) return undefined;
  if (mode === 'all') return row.tomogram_total;
  if (mode === 'annotated') return row.tomogram_selected;
  return row.subset_csv_path || row.subset_selection != null ? row.tomogram_selected : 0;
}

export interface SourcesRollup {
  sessions: number;
  totalTomograms: number;
  selectedTomograms: number;
  annotatedTomograms: number;
  copickConfigs: number;
  denoisedSessions: number;
}

export function rollup(rows: SourceRow[], mode: TomogramSubsetMode): SourcesRollup {
  return rows.reduce<SourcesRollup>(
    (acc, r) => {
      if (r.msi_session_name) acc.sessions += 1;
      if (r.denoise_run_name) acc.denoisedSessions += 1;
      acc.copickConfigs += r.selected_copick_runs.length;
      if (r.tomogram_total != null) {
        acc.totalTomograms += r.tomogram_total;
        acc.annotatedTomograms += r.tomogram_selected ?? 0;
        acc.selectedTomograms += rowSelected(r, mode) ?? 0;
      }
      return acc;
    },
    {
      sessions: 0,
      totalTomograms: 0,
      selectedTomograms: 0,
      annotatedTomograms: 0,
      copickConfigs: 0,
      denoisedSessions: 0,
    }
  );
}
