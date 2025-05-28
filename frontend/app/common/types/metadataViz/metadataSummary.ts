export interface MetadataSummaryResponse {
  session_name: string;
  run_number: string;
  num_tomograms: number;
  pixel_size: number;
  data_collection_directory: string;
  aretomo3_processing_directory: string;
  computed_metrics: ComputedMetric[];
  user_name: string;
  project_name: string;
  grid_name: string;  
}

export interface ComputedMetric {
  name: string;
  mean: number;
  median: number;
  std: number;
}
