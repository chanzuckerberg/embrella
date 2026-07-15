import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';

import { WizardLayout } from './WizardLayout';
import type { Dataset } from '../types';

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

  it('has a close button that returns to submissions', () => {
    renderWizard();
    expect(screen.getByRole('link', { name: /Close wizard/ })).toHaveAttribute('href', '/deposition/submissions');
  });

  it('skips Annotations for a tomograms-only dataset', () => {
    renderWizard(TOMOS_ONLY);
    expect(screen.getByRole('button', { name: /Step 5: Annotations \(skipped\)/ })).toBeDisabled();
  });
});
