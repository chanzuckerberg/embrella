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
  thumbnail_path: string;
  ctf_path: string;
}

export interface Metrics {
  thickness: number;
  tilt_axis: number;
  global_shift: number;
  bad_patch_low: number;
  bad_patch_all: number;
  ctf_resolution: number;
  ctf_score: number;
  defocus: number;
  extphase: number;
  pixel_size: number;
  alpha0: number;
  beta0: number;
}
export interface FilterConfig {
  filters: {
    thickness?: [number, number];
    tilt_axis?: [number, number];
    global_shift?: [number, number];
    bad_patch_low?: [number, number];
    bad_patch_all?: [number, number];
    ctf_resolution?: [number, number];
    ctf_score?: [number, number];
    defocus?: [number, number];
    extphase?: [number, number];
    alpha0?: [number, number];
    beta0?: [number, number];
  };
  filter_type: 'AND' | 'OR';
}

export interface MetricRanges {
  thickness: [number, number];
  tilt_axis: [number, number];
  global_shift: [number, number];
  bad_patch_low: [number, number];
  bad_patch_all: [number, number];
  ctf_resolution: [number, number];
  ctf_score: [number, number];
  defocus: [number, number];
  extphase: [number, number];
  pixel_size: [number, number];
  alpha0: [number, number];
  beta0: [number, number];
}
