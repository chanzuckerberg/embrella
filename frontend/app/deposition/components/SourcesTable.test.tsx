import '@testing-library/jest-dom';
import { fireEvent, render, screen, within } from '@testing-library/react';

import { SourcesTable, type SourceRow } from './SourcesTable';
import { SessionCard } from './sources/SessionCard';

jest.mock('./sources/SessionCard', () => ({
  SessionCard: jest.fn(({ onRemove, onRequestSessionChange, row }) => (
    <>
      <button onClick={onRemove}>Remove row</button>
      <button onClick={() => onRequestSessionChange({ ...row, msi_session_name: 'session-c', msi_session: null })}>
        Change row
      </button>
    </>
  )),
}));
jest.mock('./sources/DepositionSummary', () => ({ DepositionSummary: () => null }));

const row: SourceRow = {
  key: 'saved',
  id: 1,
  msi_session: 1,
  msi_session_name: 'session-a',
  aretomo_run_name: 'run1',
  denoise_run_name: '',
  subset_csv_path: '',
  selected_copick_runs: [],
};

beforeEach(() => jest.clearAllMocks());

function setup(rows: SourceRow[]) {
  const onChange = jest.fn();
  render(
    <SourcesTable
      rows={rows}
      sessionOptions={['session-a', 'session-b', 'session-c']}
      subsetMode="all"
      readOnly={false}
      onChange={onChange}
      onSubsetModeChange={jest.fn()}
      onUploadSubset={jest.fn()}
    />
  );
  return onChange;
}

it('excludes sessions selected by other rows while retaining the current selection', () => {
  setup([row, { ...row, key: 'second', id: 2, msi_session: 2, msi_session_name: 'session-b' }]);
  const calls = (SessionCard as jest.Mock).mock.calls;
  expect(calls[0][0].sessionOptions).toEqual(['session-a', 'session-c']);
  expect(calls[1][0].sessionOptions).toEqual(['session-b', 'session-c']);
});

it('requires confirmation to remove a saved session and allows cancellation', () => {
  const onChange = setup([row]);
  fireEvent.click(screen.getByText('Remove row'));
  expect(onChange).not.toHaveBeenCalled();
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'No' }));
  expect(onChange).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Remove row'));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Yes' }));
  expect(onChange).toHaveBeenCalledWith([]);
});

it('requires confirmation to switch a saved session and applies it on confirm', () => {
  const onChange = setup([row]);
  fireEvent.click(screen.getByText('Change row'));
  expect(onChange).not.toHaveBeenCalled();
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'No' }));
  expect(onChange).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Change row'));
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Yes' }));
  expect(onChange).toHaveBeenCalledWith([
    expect.objectContaining({ key: 'saved', id: 1, msi_session_name: 'session-c', msi_session: null }),
  ]);
});

it('removes an unsaved row without confirmation', () => {
  const onChange = setup([{ ...row, id: undefined }]);
  fireEvent.click(screen.getByText('Remove row'));
  expect(onChange).toHaveBeenCalledWith([]);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
