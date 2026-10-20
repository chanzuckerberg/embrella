import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';

import { WizardLayout } from './WizardLayout';
import type { Dataset } from '../types';
import { depositionKeys } from '../queryKeys';
import { resetDatasetPreparation, submitDataset } from '../services/depositionApi';

let mockServerDataset: Dataset;
jest.mock('../services/depositionApi', () => ({
  ...jest.requireActual('../services/depositionApi'),
  fetchDataset: jest.fn(() => Promise.resolve(mockServerDataset)),
  resetDatasetPreparation: jest.fn(),
  submitDataset: jest.fn(),
  fetchDatasetLogs: jest.fn(async () => ({ logs: '', source: 'none' })),
}));

const mockPush = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }));

let mockIsDirty = false;
let mockSaveError: string | null = null;
const mockSaveNow = jest.fn<Promise<boolean>, []>();
const mockDiscardChanges = jest.fn();
jest.mock('../hooks/useDraftAutoSave', () => ({
  useDraftAutoSave: () => ({
    status: mockSaveError ? 'error' : 'saved',
    isDirty: mockIsDirty,
    lastSavedAt: null,
    error: mockSaveError,
    saveNow: mockSaveNow,
    discardChanges: mockDiscardChanges,
  }),
}));

const DATASET = {
  id: 5,
  deposition: 1,
  dataset_id: 100,
  title: 'My dataset',
  description: 'Reviewed description',
  status: 'draft',
  funding: [],
  sample: { sample_type: 'in_vitro' },
  is_authors_same_as_deposition: false,
  authors_json: [{ author_id: 7, is_primary: true, is_corresponding: true, author_list_order: 0 }],
} as Dataset;
const TOMOS_ONLY = { ...DATASET, type: 'Tomos only' } as Dataset;

function renderWizard(dataset: Dataset = DATASET) {
  mockServerDataset = dataset;
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function ConnectedWizard() {
    const { data } = useQuery({
      queryKey: depositionKeys.dataset(dataset.id),
      queryFn: async () => mockServerDataset,
      initialData: dataset,
      enabled: true,
      staleTime: Infinity,
    });
    return <WizardLayout dataset={data} />;
  }
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <ConnectedWizard />
      </QueryClientProvider>
    ),
  };
}

describe('WizardLayout', () => {
  beforeEach(() => {
    (resetDatasetPreparation as jest.Mock).mockReset().mockImplementation(async () => {
      const job = { id: 1, state: 'pending', validation: null };
      mockServerDataset = { ...mockServerDataset, status: 'draft', job } as Dataset;
      return job;
    });
    (submitDataset as jest.Mock).mockReset();
    mockIsDirty = false;
    mockSaveError = null;
    mockPush.mockReset();
    mockDiscardChanges.mockReset();
    mockSaveNow.mockReset().mockResolvedValue(true);
  });

  it('starts on step 1 (Sources) with Back disabled', () => {
    renderWizard();
    expect(screen.getByText('Step 1 of 6')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled();
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

  it('jumps to a step from the stepper', async () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: /Step 3: Dataset/ }));
    expect(await screen.findByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
  });

  it('blocks Next for missing Dataset metadata while still allowing draft exit', async () => {
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: /Step 3: Dataset/ }));
    const title = await screen.findByRole('textbox', { name: /^Title/ });
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
    fireEvent.change(title, { target: { value: ' ' } });
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(screen.getByText('Dataset title is required.')).toBeInTheDocument();
    const finalize = screen.getByRole('button', { name: /Step 6:/ });
    expect(finalize).toBeDisabled();
    fireEvent.click(finalize);
    expect(screen.getByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Step 1:/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Save draft & exit' })).toBeEnabled();
    fireEvent.change(title, { target: { value: 'Corrected title' } });
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
  });

  it('requires the Deposition title but allows an empty optional description', async () => {
    const { client } = renderWizard();
    client.setQueryData(depositionKeys.deposition(1), {
      id: 1,
      title: '',
      description: '',
      authors_json: [],
      datasets: [DATASET],
    });
    fireEvent.click(screen.getByRole('button', { name: /Step 2: Deposition/ }));
    const title = await screen.findByRole('textbox', { name: /^Title/ });
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(screen.getByText('Deposition title is required.')).toBeInTheDocument();
    fireEvent.change(title, { target: { value: 'Saved deposition title' } });
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
  });

  it.each([
    { dataset: DATASET, lastMetadataStep: 5 },
    { dataset: TOMOS_ONLY, lastMetadataStep: 4 },
  ])(
    'labels the transition into Finalize, including skipped annotations ($lastMetadataStep)',
    async ({ dataset, lastMetadataStep }) => {
      renderWizard(dataset);
      fireEvent.click(screen.getByRole('button', { name: new RegExp(`Step ${lastMetadataStep}:`) }));
      expect(await screen.findByRole('button', { name: 'Next: prepare & validate' })).toBeEnabled();
    }
  );

  it('shows the server lock message and holds navigation when a stale draft cannot save', async () => {
    mockIsDirty = true;
    mockSaveError = 'Metadata is locked. Reload the page to check its current status before editing.';
    mockSaveNow.mockResolvedValue(false);
    renderWizard();
    expect(screen.getByRole('alert')).toHaveTextContent(mockSaveError);
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(mockSaveNow).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: 'Sources' })).toBeInTheDocument();
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
    expect(screen.getByText(/Only the submission owner can edit this dataset/i)).toBeInTheDocument();
  });

  it('shows no read-only notice for an owner editing a draft', () => {
    renderWizard({ ...DATASET, is_owner: true });
    expect(screen.queryByText(/read-only/i)).not.toBeInTheDocument();
  });

  it('asks to save unsaved changes before closing and stays open if saving fails', async () => {
    mockIsDirty = true;
    mockSaveNow.mockResolvedValueOnce(false);
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: 'Close wizard' }));
    expect(screen.getByRole('dialog')).toHaveTextContent('Save changes before closing?');
    expect(mockPush).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Save draft & close' }));
    await waitFor(() => expect(mockSaveNow).toHaveBeenCalledTimes(1));
    expect(mockPush).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Keep editing' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('saves and closes after confirming unsaved changes', async () => {
    mockIsDirty = true;
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: 'Close wizard' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save draft & close' }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/deposition/submissions'));
    expect(mockSaveNow).toHaveBeenCalledTimes(1);
  });

  it('confirms correction after failed validation and automatically prepares again after reset', async () => {
    (submitDataset as jest.Mock)
      .mockImplementationOnce(async () => {
        mockServerDataset = {
          ...mockServerDataset,
          status: 'syncing',
          job: {
            id: 1,
            state: 'prep_completed',
            prep_slurm_job_id: 'prep-1',
            validation: {
              status: 'failed',
              attempt: 'prep-1',
              warnings: [],
              blocking_issues: [{ message: 'Missing title' }],
            },
          },
        };
        return { state: 'prep_submitted', dataset_status: 'syncing' };
      })
      .mockImplementationOnce(async () => {
        mockServerDataset = { ...mockServerDataset, status: 'syncing', job: { id: 1, state: 'prep_submitted' } };
        return { state: 'prep_submitted', dataset_status: 'syncing' };
      });
    renderWizard({ ...DATASET, is_owner: true });
    fireEvent.click(screen.getByRole('button', { name: /Step 6:/ }));
    expect(await screen.findByText('Validation found blocking issues')).toBeInTheDocument();
    expect(resetDatasetPreparation).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /Step 3: Dataset/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'Edit metadata' }));
    const cancelledDialog = screen.getByRole('dialog');
    fireEvent.click(within(cancelledDialog).getByRole('button', { name: 'Keep read-only' }));
    await waitFor(() => expect(cancelledDialog).not.toBeInTheDocument());
    expect(resetDatasetPreparation).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Title/)).toHaveAttribute('readonly');
    fireEvent.click(screen.getByRole('button', { name: 'Edit metadata' }));
    const confirmedDialog = screen.getByRole('dialog');
    fireEvent.click(within(confirmedDialog).getByRole('button', { name: 'Edit metadata' }));
    // The modal hides the wizard from accessibility queries until its exit transition finishes.
    await waitFor(() => expect(confirmedDialog).not.toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save now' })).toBeEnabled());
    expect(screen.getByLabelText(/Title/)).not.toHaveAttribute('readonly');
    expect(resetDatasetPreparation).toHaveBeenCalledTimes(1);
    expect(mockServerDataset.status).toBe('draft');
    expect(mockServerDataset.job?.validation).toBeNull();
    fireEvent.change(screen.getByLabelText(/Title/), { target: { value: 'Corrected title' } });
    fireEvent.click(screen.getByRole('button', { name: /Step 6:/ }));
    expect(await screen.findByText('Waiting in queue')).toBeInTheDocument();
    expect(mockSaveNow).toHaveBeenCalledTimes(2);
    expect(submitDataset).toHaveBeenCalledTimes(2);
  }, 15000);

  it('retains dirty edits after a lock and requires confirmation before discarding', async () => {
    mockIsDirty = true;
    const { client } = renderWizard({ ...DATASET, is_owner: true });
    fireEvent.click(screen.getByRole('button', { name: /Step 3: Dataset/ }));
    await screen.findByRole('heading', { name: 'Dataset' });
    mockSaveNow.mockClear();
    await act(async () => {
      client.setQueryData(depositionKeys.dataset(DATASET.id), {
        ...DATASET,
        is_owner: true,
        status: 'syncing',
        job: { id: 1, state: 'prep_running' },
      });
    });
    expect(await screen.findByText(/You can copy your values from this page before closing/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Step 1: Sources/ })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(screen.getByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
    expect(mockSaveNow).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Close wizard' }));
    const discardDialog = screen.getByRole('dialog');
    expect(discardDialog).toHaveTextContent('Discard unsaved changes?');
    expect(mockPush).not.toHaveBeenCalled();
    fireEvent.click(within(discardDialog).getByRole('button', { name: 'Keep editing' }));
    await waitFor(() => expect(discardDialog).not.toBeInTheDocument());
    expect(mockDiscardChanges).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText('Close', { selector: 'button span' }));
    fireEvent.click(screen.getByRole('button', { name: 'Discard changes & close' }));
    expect(mockDiscardChanges).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledWith('/deposition/submissions');
  }, 15000);

  it('allows an explicit discard after a save failure without retrying the save', () => {
    mockIsDirty = true;
    mockSaveError = 'Metadata is locked.';
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: 'Close wizard' }));
    fireEvent.click(screen.getByRole('button', { name: 'Discard changes & close' }));
    expect(mockSaveNow).not.toHaveBeenCalled();
    expect(mockDiscardChanges).toHaveBeenCalledTimes(1);
    expect(mockPush).toHaveBeenCalledWith('/deposition/submissions');
  });

  it.each(['prep_running', 'prep_completed', 'failed', 'completed'])(
    'keeps shared metadata read-only with a %s sibling and allows continuing',
    async (state) => {
      const { client } = renderWizard({ ...DATASET, is_owner: true });
      client.setDefaultOptions({ queries: { retry: false, staleTime: Infinity } });
      client.setQueryData(depositionKeys.deposition(1), {
        id: 1,
        title: 'Shared deposition',
        authors_json: [],
        datasets: [DATASET, { ...DATASET, id: 6, job: { id: 2, state } }],
      });
      fireEvent.click(screen.getByRole('button', { name: /Step 2: Deposition/ }));
      expect(await screen.findByRole('textbox', { name: /^Title/ })).toHaveAttribute('readonly');
      expect(screen.getByText(/Editing is paused because another dataset in this submission/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: 'Next' }));
      expect(await screen.findByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
      expect(screen.getByRole('textbox', { name: /^Title/ })).not.toHaveAttribute('readonly');
    }
  );
});
