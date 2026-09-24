import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';

import { CopickConfigs } from './CopickConfigs';
import { useCopickRunObjects } from '../../hooks/useSources';
import type { SourceRow } from './types';

jest.mock('../../hooks/useSources', () => ({
  useCopickRuns: () => ({
    data: [{ name: 'run001', label: 'run001', description: '/copick/run001/config.json' }],
    isFetching: false,
  }),
  useCopickRunObjects: jest.fn(),
}));
jest.mock('../../services/depositionApi', () => ({ rescanCopick: jest.fn() }));

const mockObjects = useCopickRunObjects as jest.Mock;
afterEach(() => jest.clearAllMocks());

const row: SourceRow = {
  key: 'k1',
  msi_session: null,
  msi_session_name: 'sess',
  aretomo_run_name: 'run1',
  denoise_run_name: '',
  subset_csv_path: '',
  selected_copick_runs: ['run001'],
};

it("shows a selected config's pickable objects as chips", () => {
  mockObjects.mockReturnValue({ data: ['ribosome', 'membrane'], isFetching: false });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);
  expect(screen.getByText('ribosome')).toBeInTheDocument();
  expect(screen.getByText('membrane')).toBeInTheDocument();
});

it('shows a loading state while fetching objects', () => {
  mockObjects.mockReturnValue({ data: undefined, isFetching: true });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);
  expect(screen.getByText(/loading objects/i)).toBeInTheDocument();
});

it('renders nothing extra when a config has no objects', () => {
  mockObjects.mockReturnValue({ data: [], isFetching: false });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);
  expect(screen.queryByText(/objects:/i)).not.toBeInTheDocument();
});
