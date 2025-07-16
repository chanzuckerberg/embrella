// Object defining various metrics with their labels and units
export interface MetricConfigItem {
  label: string;
  unit: string;
}

export const METRICS_CONFIG: Record<string, MetricConfigItem> = {
  thickness: { label: 'Thickness', unit: '(Å)' },
  tilt_axis: { label: 'Tilt axis', unit: '(°)' },
  global_shift: { label: 'Global shift', unit: '(Å)' },
  bad_patch_low: { label: 'Bad patch low', unit: '(%)' },
  bad_patch_all: { label: 'Bad patch all', unit: '(%)' },
  ctf_resolution: { label: 'CTF Resolution', unit: '(Å)' },
  ctf_score: { label: 'CTF CC Score', unit: '' },
  defocus: { label: 'Defocus', unit: '(Å)' },
  extphase: { label: 'ExtPhase', unit: '(Deg)' },
  alpha0: { label: 'Alpha Offset', unit: '(°)' },
  beta0: { label: 'Beta Offset', unit: '(°)' },
};

//color mapping for scatter plot
export const SCATTERPLOT_METRIC_COLORS = {
  thickness: '#1f77b4',
  tilt_axis: '#ff7f0e',
  global_shift: '#9370DB',
  bad_patch_low: '#e377c2',
  bad_patch_all: '#58508d',
  ctf_resolution: '#17becf',
  ctf_score: '#da9100',
  defocus: '#FFD700',
  extphase: '#0B2238',
  alpha0: '#8c564b',
  beta0: '#7f7f7f',
};

// Color mapping for Histogram
export const HISTOGRAM_METRIC_COLORS = {
  thickness: '#1f77b4',
  tilt_axis: '#ff7f0e',
  global_shift: '#9370DB',
  bad_patch_low: '#e377c2',
  bad_patch_all: '#DDA0DD',
  ctf_resolution: '#17becf',
  ctf_score: '#FFD700',
  defocus: '#FF0000',
  extphase: '#0B2238',
  alpha0: '#8c564b',
  beta0: '#4B0082',
};
