import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';

import { SessionCard } from './SessionCard';
import { useAnnotatedCount } from '../../hooks/useSources';
import type { SourceRow } from './types';

jest.mock('../../hooks/useSources', () => ({
  usePlanRuns: () => ({ data: [], isFetching: false }),
  useTomogramCount: () => ({ data: 10 }),
  useAnnotatedCount: jest.fn(),
}));

const mockAnnotated = useAnnotatedCount as jest.Mock;
afterEach(() => jest.clearAllMocks());

const row: SourceRow = {
  key: 'k1',
  msi_session: null,
  msi_session_name: 'sess',
  aretomo_run_name: 'run1',
  denoise_run_name: '',
  subset_csv_path: '',
  selected_copick_runs: ['run1'],
};

// index=1 keeps the card collapsed, so only the header badge renders (no CopickConfigs hooks to mock).
function renderCard(over: Partial<SourceRow> = {}) {
  render(
    <SessionCard
      index={1}
      row={{ ...row, ...over }}
      sessionOptions={['sess']}
      subsetMode="annotated"
      readOnly={false}
      onChange={jest.fn()}
      onRemove={jest.fn()}
      onUploadSubset={jest.fn()}
    />
  );
}

it('shows "not scanned yet" instead of 0 when the annotation scan has not run', () => {
  mockAnnotated.mockReturnValue({ data: { count: 0, scanned: false }, isFetching: false });
  renderCard();
  expect(screen.getByText(/not scanned yet/i)).toBeInTheDocument();
});

it('shows a real 0 count once the scan has completed', () => {
  mockAnnotated.mockReturnValue({ data: { count: 0, scanned: true }, isFetching: false });
  renderCard();
  expect(screen.getByText(/0 \/ 10 tomograms/i)).toBeInTheDocument();
  expect(screen.queryByText(/not scanned yet/i)).not.toBeInTheDocument();
});

it('shows the scanning state while the scan is in flight', () => {
  mockAnnotated.mockReturnValue({ data: undefined, isFetching: true });
  renderCard();
  expect(screen.getByText(/scanning annotations/i)).toBeInTheDocument();
});

it('does not say "not scanned yet" when no copick config is selected', () => {
  mockAnnotated.mockReturnValue({ data: undefined, isFetching: false, isError: false });
  renderCard({ selected_copick_runs: [] });
  expect(screen.queryByText(/not scanned yet/i)).not.toBeInTheDocument();
  expect(screen.getByText(/- \/ 10 tomograms/i)).toBeInTheDocument();
});

it('shows "count unavailable" when the scan request errors', () => {
  mockAnnotated.mockReturnValue({ data: undefined, isFetching: false, isError: true });
  renderCard();
  expect(screen.getByText(/count unavailable/i)).toBeInTheDocument();
  expect(screen.queryByText(/not scanned yet/i)).not.toBeInTheDocument();
});

it('does not flicker to "scanning" during a background poll (data present, refetching)', () => {
  mockAnnotated.mockReturnValue({ data: { count: 0, scanned: false }, isFetching: true, isError: false });
  renderCard();
  expect(screen.getByText(/not scanned yet/i)).toBeInTheDocument();
  expect(screen.queryByText(/scanning annotations/i)).not.toBeInTheDocument();
});
