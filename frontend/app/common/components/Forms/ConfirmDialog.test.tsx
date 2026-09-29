import '@testing-library/jest-dom';
import { fireEvent, render, screen, within } from '@testing-library/react';

import { ConfirmDialog } from './ConfirmDialog';

function setup(overrides = {}) {
  const onClose = jest.fn();
  const onConfirm = jest.fn();
  render(
    <ConfirmDialog
      open
      onClose={onClose}
      onConfirm={onConfirm}
      title="Delete thing?"
      heading="This deletes everything."
      body="Cannot be undone."
      {...overrides}
    />
  );
  return { onClose, onConfirm };
}

it('renders the title, heading, and body', () => {
  setup();
  expect(screen.getByText('Delete thing?')).toBeInTheDocument();
  expect(screen.getByText('This deletes everything.')).toBeInTheDocument();
  expect(screen.getByText('Cannot be undone.')).toBeInTheDocument();
});

it('fires onConfirm and onClose from the buttons', () => {
  const { onClose, onConfirm } = setup();
  const dialog = screen.getByRole('dialog');
  fireEvent.click(within(dialog).getByRole('button', { name: 'No' }));
  expect(onClose).toHaveBeenCalledTimes(1);
  fireEvent.click(within(dialog).getByRole('button', { name: 'Yes' }));
  expect(onConfirm).toHaveBeenCalledTimes(1);
});

it('confirms on Enter unless submitting', () => {
  const { onConfirm } = setup();
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Enter' });
  expect(onConfirm).toHaveBeenCalledTimes(1);
});

it('does not confirm when Enter is pressed on a button (avoids double-fire and No/close hijack)', () => {
  const { onConfirm } = setup();
  const dialog = screen.getByRole('dialog');
  fireEvent.keyDown(within(dialog).getByRole('button', { name: 'No' }), { key: 'Enter' });
  fireEvent.keyDown(within(dialog).getByRole('button', { name: 'Yes' }), { key: 'Enter' });
  expect(onConfirm).not.toHaveBeenCalled();
});

it('shows the submitting label and disables the buttons while submitting', () => {
  const { onConfirm } = setup({ isSubmitting: true, submittingText: 'Deleting...' });
  const dialog = screen.getByRole('dialog');
  expect(within(dialog).getByRole('button', { name: 'Deleting...' })).toBeDisabled();
  expect(within(dialog).getByRole('button', { name: 'No' })).toBeDisabled();
  fireEvent.keyDown(dialog, { key: 'Enter' });
  expect(onConfirm).not.toHaveBeenCalled();
});

it('surfaces an error message when provided', () => {
  setup({ error: 'Failed to delete' });
  expect(screen.getByText('Failed to delete')).toBeInTheDocument();
});

it('uses custom confirm and cancel labels', () => {
  setup({ confirmText: 'Trash it', cancelText: 'Keep' });
  const dialog = screen.getByRole('dialog');
  expect(within(dialog).getByRole('button', { name: 'Trash it' })).toBeInTheDocument();
  expect(within(dialog).getByRole('button', { name: 'Keep' })).toBeInTheDocument();
});
