import '@testing-library/jest-dom';
import { act, render, screen } from '@testing-library/react';

import { SourcesStep } from './SourcesStep';
import { SourcesTable, type SourceRow } from '../../components/SourcesTable';
import { updateDataset } from '../../services/depositionApi';
import type { Dataset } from '../../types';

jest.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ setQueryData: jest.fn(), invalidateQueries: jest.fn() }),
}));
jest.mock('../../hooks/useSources', () => ({
  useMsiSessions: () => ({ data: ['session-a', 'session-b'] }),
}));
jest.mock('../../services/depositionApi', () => ({
  updateDataset: jest.fn(),
  getMsiSessionId: jest.fn().mockResolvedValue(1),
}));
jest.mock('../../components/SourcesTable', () => ({ SourcesTable: jest.fn(() => null) }));

const dataset = {
  id: 1,
  status: 'draft',
  sessions: [{ id: 10, msi_session: 1, msi_session_name: 'session-a', aretomo_run_name: 'run1' }],
} as Dataset;

function tableProps() {
  return (SourcesTable as jest.Mock).mock.calls.at(-1)[0];
}

beforeEach(() => {
  jest.useFakeTimers();
  jest.clearAllMocks();
  (updateDataset as jest.Mock).mockResolvedValue(dataset);
});
afterEach(() => jest.useRealTimers());

it('does not delete a saved session when cleared, including autosave and unmount', async () => {
  const { unmount } = render(<SourcesStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  const props = tableProps();
  act(() => props.onChange([{ ...props.rows[0], msi_session_name: '', msi_session: null }]));
  expect(screen.getByRole('alert')).toHaveTextContent('Select an imaging session');
  await act(async () => jest.advanceTimersByTime(5000));
  unmount();
  expect(updateDataset).not.toHaveBeenCalled();
});

it('blocks duplicate sessions and saves again once the duplicate is removed', async () => {
  render(<SourcesStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  const props = tableProps();
  const original: SourceRow = props.rows[0];
  act(() => props.onChange([original, { ...original, key: 'new', id: undefined, aretomo_run_name: 'run2' }]));
  await act(async () => jest.advanceTimersByTime(5000));
  expect(updateDataset).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toHaveTextContent('only be selected once');
  act(() => tableProps().onChange([original]));
  await act(async () => jest.advanceTimersByTime(5000));
  expect(updateDataset).toHaveBeenCalledWith(
    1,
    expect.objectContaining({
      sessions: [expect.objectContaining({ id: 10, aretomo_run_name: 'run1' })],
    })
  );
});

it('allows an unused blank new row without dropping existing sessions', async () => {
  render(<SourcesStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  const props = tableProps();
  act(() => props.onChange([...props.rows, { ...props.rows[0], key: 'new', id: undefined, msi_session_name: '' }]));
  await act(async () => jest.advanceTimersByTime(5000));
  expect(updateDataset).toHaveBeenCalledWith(
    1,
    expect.objectContaining({
      sessions: [expect.objectContaining({ id: 10 })],
    })
  );
});
