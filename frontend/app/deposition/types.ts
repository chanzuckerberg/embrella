export type DatasetStatus = 'draft' | 'syncing' | 'pushed' | 'failed';

export interface AuthorRef {
  author_id: number; // soft-ref to People.Person
  is_primary: boolean;
  is_corresponding: boolean;
  author_list_order: number;
}

export interface DatasetFunding {
  id?: number;
  funding_agency_name: string;
  grant_id?: string;
}

export type JobState =
  | 'pending'
  | 'prep_submitted'
  | 'prep_running'
  | 'prep_completed'
  | 'push_submitted'
  | 'push_running'
  | 'completed'
  | 'failed';

export interface DatasetJob {
  id: number;
  state: JobState;
  prep_slurm_job_id?: string | null;
  push_slurm_job_id?: string | null;
  error_message?: string | null;
}
export interface Institution {
  id: number;
  name: string;
  ror_id?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
}

export interface Person {
  id: number;
  orcid?: string | null;
  given_name: string;
  family_name: string;
  contact_email?: string | null;
  institution?: Institution | null;
}

export type CrossRefType = 'publication' | 'related_db';
export interface CrossRef {
  type: CrossRefType;
  value: string;
}
export type MethodLinkType = 'documentation' | 'models_weights' | 'other' | 'source_code' | 'website';

export interface DepositionMethodLink {
  id?: number;
  annotation: number;
  link_type: MethodLinkType;
  link: string;
  custom_name?: string;
}

export interface CopickRunOption {
  name: string;
  label: string;
  description?: string;
}

export type TomogramSubsetMode = 'all' | 'annotated' | 'custom';

export interface DepositionSession {
  id: number;
  msi_session: number;
  msi_session_name?: string;
  aretomo_run_name?: string;
  denoise_run_name?: string;
  subset_csv_path?: string;
  selected_copick_runs?: unknown[];
  tiltseries_metadata?: Record<string, unknown> | null;
  tomogram_metadata?: Record<string, unknown> | null;
  annotations?: unknown[];
  last_autofill_at?: string | null;
  last_autofill_duration_seconds?: number | null;
}

export interface DatasetSample {
  sample_type?: string;
  organism_name?: string;
  organism_taxid?: number | null;
  tissue_name?: string;
  tissue_id?: string;
  cell_name?: string;
  cell_type_id?: string;
  cell_strain_name?: string;
  cell_strain_id?: string;
  cell_component_name?: string;
  ontology?: string; // cell-component ontology id (e.g. GO:0005886)
  development_stage_name?: string;
  development_stage_ontology_id?: string;
  disease_name?: string;
  disease_ontology_id?: string;
}

export interface Dataset {
  id: number;
  deposition: number;
  dataset_id?: number | null;
  title: string;
  description?: string;
  sample_preparation?: string;
  grid_preparation?: string;
  other_setup?: string;
  assay_label?: string;
  assay_ontology_id?: string;
  is_authors_same_as_deposition?: boolean;
  status: DatasetStatus;
  sample?: DatasetSample | null;
  authors_json?: AuthorRef[];
  dataset_publications?: string;
  related_database_entries?: string;
  tomogram_subset_mode?: TomogramSubsetMode;
  funding?: DatasetFunding[];
  sessions?: DepositionSession[];
  job?: DatasetJob | null;
  updated_at?: string;
  session_names?: string[];
  session_count?: number;
  type?: string;
  is_owner?: boolean;
}

export interface Deposition {
  id: number;
  deposition_id?: number | null;
  title: string;
  description?: string;
  submitter_username?: string;
  deposition_publications?: string;
  related_database_entries?: string;
  authors_json?: AuthorRef[];
  release_date?: string | null;
  datasets?: Dataset[];
  is_owner?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SubmissionList {
  submissions: Deposition[];
  total_count: number;
}
