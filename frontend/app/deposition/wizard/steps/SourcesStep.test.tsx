import '@testing-library/jest-dom';
import { act, render, screen } from '@testing-library/react';

import { SourcesStep } from './SourcesStep';
import { SourcesTable, type SourceRow } from '../../components/SourcesTable';
import { deleteSession, getMsiSessionId, updateDataset } from '../../services/depositionApi';
import type { Dataset } from '../../types';

jest.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ setQueryData: jest.fn(), invalidateQueries: jest.fn() }),
}));
jest.mock('../../hooks/useSources', () => ({
  useMsiSessions: () => ({ data: ['session-a', 'session-b'] }),
}));
jest.mock('../../services/depositionApi', () => ({
  updateDataset: jest.fn(),
  deleteSession: jest.fn(),
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
  (deleteSession as jest.Mock).mockResolvedValue(undefined);
  (getMsiSessionId as jest.Mock).mockResolvedValue(1);
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

it('explicitly deletes a saved session before removing its row', async () => {
  let finishDelete!: () => void;
  (deleteSession as jest.Mock).mockReturnValue(
    new Promise<void>((resolve) => {
      finishDelete = resolve;
    })
  );
  (updateDataset as jest.Mock).mockResolvedValue({ ...dataset, sessions: [] });
  render(<SourcesStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  await act(async () => tableProps().onRemoveSession(tableProps().rows[0]));
  expect(deleteSession).toHaveBeenCalledWith(10);
  expect(tableProps().rows).toHaveLength(1);
  expect(tableProps().readOnly).toBe(true);
  await act(async () => finishDelete());
  expect(tableProps().rows).toEqual([]);
  await act(async () => jest.advanceTimersByTime(5000));
  expect(updateDataset).toHaveBeenCalledWith(1, expect.objectContaining({ sessions: [] }));
});

it('deletes the old session before saving a replacement without its old id', async () => {
  (getMsiSessionId as jest.Mock).mockResolvedValue(2);
  (updateDataset as jest.Mock).mockResolvedValue({
    ...dataset,
    sessions: [{ id: 11, msi_session: 2, msi_session_name: 'session-b' }],
  });
  render(<SourcesStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  const original = tableProps().rows[0];
  await act(async () =>
    tableProps().onChangeSession(original, {
      ...original,
      msi_session: null,
      msi_session_name: 'session-b',
      aretomo_run_name: '',
    })
  );
  expect(deleteSession).toHaveBeenCalledWith(10);
  expect(updateDataset).not.toHaveBeenCalled();
  await act(async () => jest.advanceTimersByTime(5000));
  const payload = (updateDataset as jest.Mock).mock.calls[0][1].sessions;
  expect(payload).toEqual([expect.objectContaining({ msi_session: 2 })]);
  expect(payload[0]).not.toHaveProperty('id');
  expect(tableProps().rows[0].id).toBe(11);
});

it.each(['remove', 'switch'])('keeps the old session and shows a failed delete on %s', async (action) => {
  (deleteSession as jest.Mock).mockRejectedValue(new Error('Deletion is locked. Reset preparation first.'));
  render(<SourcesStep dataset={dataset} readOnly={false} reportSave={jest.fn()} />);
  const original = tableProps().rows[0];
  await act(async () => {
    if (action === 'remove') tableProps().onRemoveSession(original);
    else tableProps().onChangeSession(original, { ...original, msi_session: 2, msi_session_name: 'session-b' });
  });
  expect(screen.getByRole('alert')).toHaveTextContent('Deletion is locked');
  expect(tableProps().rows[0]).toEqual(original);
  await act(async () => jest.advanceTimersByTime(5000));
  expect(updateDataset).not.toHaveBeenCalled();
});

it('refuses navigation while a switch is deleting, then saves the replacement', async () => {
  (getMsiSessionId as jest.Mock).mockResolvedValue(2);
  (updateDataset as jest.Mock).mockResolvedValue({
    ...dataset,
    sessions: [{ id: 11, msi_session: 2, msi_session_name: 'session-b' }],
  });
  let finishDelete!: () => void;
  (deleteSession as jest.Mock).mockReturnValue(
    new Promise<void>((resolve) => {
      finishDelete = resolve;
    })
  );
  const reportSave = jest.fn();
  render(<SourcesStep dataset={dataset} readOnly={false} reportSave={reportSave} />);
  const original = tableProps().rows[0];
  await act(async () =>
    tableProps().onChangeSession(original, {
      ...original,
      msi_session: null,
      msi_session_name: 'session-b',
      aretomo_run_name: '',
    })
  );
  // While the delete is pending the step is busy and navigation is refused, so no PATCH runs.
  const during = reportSave.mock.calls.at(-1)![0];
  expect(during.status).toBe('saving');
  expect(await during.saveNow()).toBe(false);
  expect(updateDataset).not.toHaveBeenCalled();
  // Once the delete resolves, the replacement is dirty and saveNow saves it without the old id.
  await act(async () => finishDelete());
  const after = reportSave.mock.calls.at(-1)![0];
  await act(async () => {
    await after.saveNow();
  });
  const payload = (updateDataset as jest.Mock).mock.calls[0][1].sessions;
  expect(payload).toEqual([expect.objectContaining({ msi_session: 2 })]);
  expect(payload[0]).not.toHaveProperty('id');
});

it.each(['syncing', 'pushed'])('keeps %s datasets read-only', (status) => {
  render(<SourcesStep dataset={{ ...dataset, status } as Dataset} readOnly reportSave={jest.fn()} />);
  expect(tableProps().readOnly).toBe(true);
});

it('keeps a failed dataset read-only for a viewer without edit permission', () => {
  render(<SourcesStep dataset={{ ...dataset, status: 'failed' }} readOnly reportSave={jest.fn()} />);
  expect(tableProps().readOnly).toBe(true);
});
