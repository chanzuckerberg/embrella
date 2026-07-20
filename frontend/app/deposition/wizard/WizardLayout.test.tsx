import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { WizardLayout } from './WizardLayout';
import type { Dataset } from '../types';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }));

const DATASET = { id: 5, deposition: 1, dataset_id: 100, title: 'My dataset', status: 'draft', funding: [] } as Dataset;
const TOMOS_ONLY = { ...DATASET, type: 'Tomos only' } as Dataset;

function renderWizard(dataset: Dataset = DATASET) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WizardLayout dataset={dataset} />
    </QueryClientProvider>,
  );
}

describe('WizardLayout', () => {
  it('starts on step 1 (Sources) with Back disabled', () => {
    renderWizard();
    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled();
  });

  it('advances to the next step via Next', () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByRole('heading', { name: 'Deposition' })).toBeInTheDocument();
  });

  it('jumps to a step from the stepper', () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: /Step 3: Dataset/ }));
    expect(screen.getByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
  });

  it('closes back to submissions', async () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: /Close wizard/ }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/deposition/submissions'));
  });

  it('skips Annotations for a tomograms-only dataset', () => {
    renderWizard(TOMOS_ONLY);
    expect(screen.getByRole('button', { name: /Step 5: Annotations \(skipped\)/ })).toBeDisabled();
  });

  it('shows a read-only notice when the user is not the deposition owner', () => {
    renderWizard({ ...DATASET, is_owner: false } as Dataset);
    expect(screen.getByText(/read-only/i)).toBeInTheDocument();
  });

  it('shows no read-only notice for the owner', () => {
    renderWizard({ ...DATASET, is_owner: true } as Dataset);
    expect(screen.queryByText(/read-only/i)).not.toBeInTheDocument();
  });
});
