export interface SourceRow {
  key: string;
  id?: number;
  msi_session: number | null;
  msi_session_name: string;
  aretomo_run_name: string;
  denoise_run_name: string;
  subset_csv_path: string;
  subset_input_mode?: 'upload' | 'path';
  selected_copick_runs: string[];
  tomogram_total?: number;
  tomogram_selected?: number;
}

export const NONE_RUN = '__none__';
