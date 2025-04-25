export interface MetadataVizResponse {
  session_name: string;
  run_number: string;
  num_tomograms: number;
  filters_applied?: FiltersApplied;
  metric_ranges: MetricRanges;
  result: TiltSeries[];
}

export interface TiltSeries {
  name: string;
  metrics: Metrics;
}

export interface Metrics {
  thickness_pix: number;
  tilt_axis: number;
  global_shift_pix: number;
  bad_patch_low: number;
  bad_patch_all: number;
  ctf_resolution_a: number;
  ctf_score: number;
  df_hand: number;
  pixel_size_a: number;
  cs_nm: number;
  kv: number;
  alpha0: number;
  beta0: number;
}

export interface FiltersApplied {
  thickness_pix?: [number, number];
  tilt_axis?: [number, number];
  global_shift_pix?: [number, number];
  bad_patch_low?: [number, number];
  bad_patch_all?: [number, number];
  ctf_resolution_a?: [number, number];
  ctf_score?: [number, number];
}

export interface MetricRanges {
  thickness_pix: [number, number];
  tilt_axis: [number, number];
  global_shift_pix: [number, number];
  bad_patch_low: [number, number];
  bad_patch_all: [number, number];
  ctf_resolution_a: [number, number];
  ctf_score: [number, number];
  df_hand: [number, number];
  pixel_size_a: [number, number];
  cs_nm: [number, number];
  kv: [number, number];
  alpha0: [number, number];
  beta0: [number, number];
}