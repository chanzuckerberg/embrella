import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { ReservationModal } from './ReservationModal';
import { useSubmissions } from '../../hooks/useSubmissions';
import type { Deposition } from '../../types';

jest.mock('../../hooks/useSubmissions', () => ({ useSubmissions: jest.fn() }));
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }));

const mockUseSubmissions = useSubmissions as jest.Mock;

const DEP = {
  id: 1,
  deposition_id: 10337,
  title: 'Test dep',
  datasets: [{ id: 5, deposition: 1, dataset_id: 100, title: 'DS one', status: 'draft' }],
} as Deposition;

function renderModal(props: Partial<React.ComponentProps<typeof ReservationModal>> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ReservationModal open onClose={jest.fn()} {...props} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockPush.mockClear();
  mockUseSubmissions.mockReturnValue({ data: { submissions: [DEP], total_count: 1 } });
});

describe('ReservationModal', () => {
  it('New Submission shows the three options', () => {
    renderModal();
    expect(screen.getByText('New submission')).toBeInTheDocument();
    expect(screen.getByText('Reserve or select IDs')).toBeInTheDocument();
    expect(screen.getByText('Reserve new deposition + dataset')).toBeInTheDocument();
    expect(screen.getByText('Use existing deposition')).toBeInTheDocument();
    expect(screen.getByText('Reuse existing dataset')).toBeInTheDocument();
  });

  it('Add dataset scopes to the dataset choice and hides the option cards', () => {
    renderModal({ initialMode: 'existing_deposition', lockedDeposition: DEP });
    expect(screen.getByText('Add dataset')).toBeInTheDocument();
    expect(screen.getByText('Add a dataset to cdp-10337')).toBeInTheDocument();
    // option cards are not rendered in the add-dataset flow
    expect(screen.queryByText('Reserve new deposition + dataset')).not.toBeInTheDocument();
    // the dataset choice is shown
    expect(screen.getByText('Reserve new dataset under this deposition')).toBeInTheDocument();
  });

  it('Continue is disabled for "reuse existing dataset" until one is picked', () => {
    renderModal({ initialMode: 'reuse_dataset' });
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
  });

  it('Continue is disabled for "existing deposition" until a deposition is picked', () => {
    renderModal({ initialMode: 'existing_deposition' });
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
  });

  it('reusing an existing dataset routes to the wizard (no reservation)', async () => {
    renderModal({ initialMode: 'reuse_dataset' });
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(screen.getByRole('option', { name: /ds-100/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/deposition/wizard/5'));
  });
});
