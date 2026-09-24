import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

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

it("shows a selected config's pickable objects as chips with a count", () => {
  mockObjects.mockReturnValue({ data: ['ribosome', 'membrane'], isFetching: false });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);
  expect(screen.getByText('2 objects:')).toBeInTheDocument();
  expect(screen.getByText('ribosome')).toBeInTheDocument();
  expect(screen.getByText('membrane')).toBeInTheDocument();
});

it('caps the object chips and expands via "+N more"', async () => {
  const objects = Array.from({ length: 8 }, (_, i) => `obj${i + 1}`);
  mockObjects.mockReturnValue({ data: objects, isFetching: false });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);

  // Only the first 5 are shown initially; the rest hide behind "+3 more".
  expect(screen.getByText('obj5')).toBeInTheDocument();
  expect(screen.queryByText('obj6')).not.toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: /\+3 more/i }));
  expect(screen.getByText('obj8')).toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: /show less/i }));
  expect(screen.queryByText('obj6')).not.toBeInTheDocument();
});

it('shows a loading state while fetching objects', () => {
  mockObjects.mockReturnValue({ data: undefined, isFetching: true });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);
  expect(screen.getByText(/loading objects/i)).toBeInTheDocument();
});

it('warns when a selected config defines no objects', () => {
  mockObjects.mockReturnValue({ data: [], isFetching: false });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);
  expect(screen.getByText(/no objects defined/i)).toBeInTheDocument();
});

it('shows an unavailable state when the objects request errors', () => {
  mockObjects.mockReturnValue({ data: undefined, isFetching: false, isError: true });
  render(<CopickConfigs row={row} readOnly={false} onChange={jest.fn()} />);
  expect(screen.getByText(/objects unavailable/i)).toBeInTheDocument();
});
