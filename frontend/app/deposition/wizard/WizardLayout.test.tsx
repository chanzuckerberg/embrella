import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';

import { WizardLayout } from './WizardLayout';
import type { Dataset } from '../types';

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }));

const mockSaveNow = jest.fn<Promise<boolean>, []>();
jest.mock('../hooks/useDraftAutoSave', () => ({
  useDraftAutoSave: () => ({ status: 'saved', lastSavedAt: null, saveNow: mockSaveNow }),
}));

const DATASET = { id: 5, deposition: 1, dataset_id: 100, title: 'My dataset', status: 'draft', funding: [] } as Dataset;
const TOMOS_ONLY = { ...DATASET, type: 'Tomos only' } as Dataset;

function renderWizard(dataset: Dataset = DATASET) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WizardLayout dataset={dataset} />
    </QueryClientProvider>
  );
}

describe('WizardLayout', () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockSaveNow.mockReset().mockResolvedValue(true);
  });

  it('starts on step 1 (Sources) with Back disabled', () => {
    renderWizard();
    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled();
  });

  it('advances to the next step via Next', async () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByRole('heading', { name: 'Deposition' })).toBeInTheDocument();
  });

  it.each([true, false])('shows Saving… until the next-step save resolves with %s', async (success) => {
    let finish!: (value: boolean) => void;
    mockSaveNow.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        })
    );
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
    expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Saving…' }));
    expect(mockSaveNow).toHaveBeenCalledTimes(1);
    await act(async () => {
      finish(success);
    });
    expect(screen.queryByRole('button', { name: 'Saving…' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: success ? 'Deposition' : 'Sources' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).toBeInTheDocument();
  });

  it('stays on the current step when saving before Next fails', async () => {
    mockSaveNow.mockResolvedValueOnce(false);
    renderWizard();

    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    await waitFor(() => expect(mockSaveNow).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Deposition' })).not.toBeInTheDocument();
  });

  it('jumps to a step from the stepper', async () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: /Step 3: Dataset/ }));
    expect(await screen.findByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
  });

  it('closes back to submissions', async () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: /Close wizard/ }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/deposition/submissions'));
  });

  it('does not exit when saving the draft fails', async () => {
    mockSaveNow.mockResolvedValueOnce(false);
    renderWizard();

    fireEvent.click(screen.getByRole('button', { name: /Save draft & exit/ }));

    await waitFor(() => expect(mockSaveNow).toHaveBeenCalled());
    expect(mockPush).not.toHaveBeenCalled();
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
