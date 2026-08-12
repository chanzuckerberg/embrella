import { rollup, rowSelected, subsetCount } from './counts';
import type { SourceRow } from './types';

function row(over: Partial<SourceRow> = {}): SourceRow {
  return {
    key: 'k',
    msi_session: 1,
    msi_session_name: '25nov13a',
    aretomo_run_name: 'run001',
    denoise_run_name: '',
    subset_csv_path: '',
    selected_copick_runs: [],
    tomogram_total: 100,
    ...over,
  };
}

describe('subsetCount', () => {
  it('counts a metadata-viewer JSON selection', () => {
    expect(subsetCount(row({ subset_selection: { 'Selected positions': ['P_1', 'P_2', 'P_3'] } }))).toBe(3);
  });

  it('counts a parsed CSV (list of rows)', () => {
    expect(subsetCount(row({ subset_selection: [{ Tilt_Series: 'P_1.mrc' }, { Tilt_Series: 'P_2.mrc' }] }))).toBe(2);
  });

  it('returns undefined when there is no usable selection', () => {
    expect(subsetCount(row({ subset_selection: undefined }))).toBeUndefined();
    expect(subsetCount(row({ subset_selection: { other: 1 } }))).toBeUndefined();
  });
});

describe('rowSelected', () => {
  it('all → every tomogram', () => {
    expect(rowSelected(row(), 'all')).toBe(100);
  });

  it('annotated → uses the (pending) scan count', () => {
    expect(rowSelected(row({ tomogram_selected: undefined }), 'annotated')).toBeUndefined();
    expect(rowSelected(row({ tomogram_selected: 40 }), 'annotated')).toBe(40);
  });

  it('custom → counts an uploaded subset, capped at total', () => {
    expect(rowSelected(row({ subset_selection: { 'Selected positions': ['a', 'b'] } }), 'custom')).toBe(2);
    expect(
      rowSelected(row({ tomogram_total: 1, subset_selection: { 'Selected positions': ['a', 'b'] } }), 'custom')
    ).toBe(1);
  });

  it('custom → 0 when nothing is uploaded, undefined for a cluster path', () => {
    expect(rowSelected(row(), 'custom')).toBe(0);
    expect(rowSelected(row({ subset_csv_path: '/hpc/x.csv' }), 'custom')).toBeUndefined();
  });

  it('undefined when the total is unknown', () => {
    expect(rowSelected(row({ tomogram_total: undefined }), 'all')).toBeUndefined();
  });
});

describe('rollup', () => {
  const rows = [
    row({ key: 'a', tomogram_total: 100, subset_selection: { 'Selected positions': ['x', 'y', 'z'] } }),
    row({ key: 'b', tomogram_total: 50, denoise_run_name: 'run003', selected_copick_runs: ['run002'] }),
  ];

  it('all → selected equals total, nothing dropped', () => {
    const s = rollup(rows, 'all');
    expect(s.sessions).toBe(2);
    expect(s.totalTomograms).toBe(150);
    expect(s.selectedTomograms).toBe(150);
    expect(s.droppedTomograms).toBe(0);
    expect(s.copickConfigs).toBe(1);
    expect(s.denoisedSessions).toBe(1);
  });

  it('custom → selected sums subset counts, dropped is the remainder', () => {
    const s = rollup(rows, 'custom');
    expect(s.selectedTomograms).toBe(3); // 3 from row a, 0 from row b (no subset)
    expect(s.droppedTomograms).toBe(147); // 150 - 3
  });
});
