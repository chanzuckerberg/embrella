export interface MetadataVizResponse {
  session_name: string;
  run_number: string;
  filters_applied?: FilterConfig;
  num_tomograms: number;
  metric_ranges: MetricRanges;
  accepted_results: TiltSeries[];
  rejected_results: TiltSeries[];
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
  pixel_size_a: number;
  alpha0: number;
  beta0: number;
}
export interface FilterConfig {
  filters: {
    thickness_pix?: [number, number];
    tilt_axis?: [number, number];
    global_shift_pix?: [number, number];
    bad_patch_low?: [number, number];
    bad_patch_all?: [number, number];
    ctf_resolution_a?: [number, number];
    ctf_score?: [number, number];
    alpha0?: [number, number];
    beta0?: [number, number];
  };
  filter_type: 'AND' | 'OR';
}

export interface MetricRanges {
  thickness_pix: [number, number];
  tilt_axis: [number, number];
  global_shift_pix: [number, number];
  bad_patch_low: [number, number];
  bad_patch_all: [number, number];
  ctf_resolution_a: [number, number];
  ctf_score: [number, number];
  pixel_size_a: [number, number];
  alpha0: [number, number];
  beta0: [number, number];
}
