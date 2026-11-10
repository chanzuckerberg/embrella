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
  // Steps fetch these on mount; stub them so the suite never touches the network (slow + flaky in CI).
  fetchDeposition: jest.fn(async () => ({
    id: 1,
    title: 'Deposition title',
    description: '',
    authors_json: [],
    datasets: [mockServerDataset],
  })),
  fetchPeopleByIds: jest.fn(async () => []),
  listMsiSessions: jest.fn(async () => []),
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

// DatasetForm is the heavy form and has its own suite, so stub it here to keep its large MUI tree
// out of the render path. DepositionForm stays real (it has no own test, and costs ~0.4s). The real
// DatasetStep/DepositionStep wrappers still run, so the sibling-lock notice and gating are real.
jest.mock('../datasets/[id]/DatasetForm', () => {
  const { useEffect } = jest.requireActual('react');
  return {
    DatasetForm: ({
      dataset,
      reportSave,
      reportBlocking,
      readOnly,
    }: {
      dataset: { metadata_issues?: string[]; title?: string };
      reportSave?: (s: unknown) => void;
      reportBlocking?: (n: number) => void;
      readOnly?: boolean;
    }) => {
      const issues = dataset.metadata_issues ?? [];
      useEffect(() => reportBlocking?.(readOnly ? 0 : issues.length), [readOnly, issues.length, reportBlocking]);
      useEffect(
        () =>
          reportSave?.({
            status: mockSaveError ? 'error' : 'saved',
            isDirty: mockIsDirty,
            lastSavedAt: null,
            error: mockSaveError,
            saveNow: mockSaveNow,
            discardChanges: mockDiscardChanges,
          }),
        [reportSave]
      );
      return (
        <div>
          <input aria-label="Title" defaultValue={dataset.title ?? ''} readOnly={readOnly} />
          {!readOnly && issues.map((m, i) => <p key={i}>{m}</p>)}
        </div>
      );
    },
  };
});

const DATASET = {
  id: 5,
  deposition: 1,
  dataset_id: 100,
  title: 'My dataset',
  description: 'Reviewed description',
  status: 'draft',
  funding: [],
  metadata_issues: [],
  sample: { sample_type: 'in_vitro' },
  is_authors_same_as_deposition: false,
  authors_json: [{ author_id: 7, is_primary: true, is_corresponding: true, author_list_order: 0 }],
} as Dataset;

function renderWizard(dataset: Dataset = DATASET) {
  mockServerDataset = dataset;
  // staleTime Infinity: seeded setQueryData is never refetched, so steps read the test's data
  // instead of racing a network refetch that overwrites it or errors.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity, gcTime: Infinity } },
  });
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

  it('blocks Next for missing Dataset metadata while still allowing draft exit', async () => {
    const { client } = renderWizard({ ...DATASET, metadata_issues: ['Dataset title is required.'] });
    // Navigation stays mounted across steps; avoid rescanning the full Dataset form for each assertion.
    const next = screen.getByRole('button', { name: 'Next' });
    const finalize = screen.getByRole('button', { name: /Step 6:/ });
    const sources = screen.getByRole('button', { name: /Step 1:/ });
    const exit = screen.getByRole('button', { name: 'Save draft & exit' });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Step 3: Dataset/ }));
    });
    const title = screen.getByLabelText(/^Title/);
    expect(next).toBeDisabled();
    expect(screen.getByText('Dataset title is required.')).toBeInTheDocument();
    expect(finalize).toBeDisabled();
    fireEvent.click(finalize);
    expect(screen.getByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
    expect(sources).toBeEnabled();
    expect(exit).toBeEnabled();
    fireEvent.change(title, { target: { value: 'Corrected title' } });
    // Only the saved backend result can clear the gate.
    expect(next).toBeDisabled();
    await act(async () => {
      client.setQueryData(depositionKeys.dataset(DATASET.id), { ...DATASET, metadata_issues: [] });
    });
    await waitFor(() => expect(next).toBeEnabled());
  });

  it('requires the Deposition title but allows an empty optional description', async () => {
    const { client } = renderWizard();
    const next = screen.getByRole('button', { name: 'Next' });
    client.setQueryData(depositionKeys.deposition(1), {
      id: 1,
      title: '',
      description: '',
      authors_json: [],
      datasets: [DATASET],
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Step 2: Deposition/ }));
    });
    const title = screen.getByLabelText(/^Title/);
    expect(next).toBeDisabled();
    expect(screen.getByText('Deposition title is required.')).toBeInTheDocument();
    fireEvent.change(title, { target: { value: 'Saved deposition title' } });
    expect(next).toBeEnabled();
  });

  it('reaches Finalize without preparing, then starts on the Start button', async () => {
    (submitDataset as jest.Mock).mockImplementation(async () => {
      mockServerDataset = { ...mockServerDataset, status: 'syncing', job: { id: 1, state: 'prep_submitted' } };
      return { state: 'prep_submitted', dataset_status: 'syncing' };
    });
    renderWizard();
    fireEvent.click(screen.getByRole('button', { name: /Step 5: Annotations/ }));
    fireEvent.click(await screen.findByRole('button', { name: 'Next' }));
    // Finalize screen must not start preparation on its own.
    expect(submitDataset).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole('button', { name: 'Start preparation' }));
    await waitFor(() => expect(submitDataset).toHaveBeenCalledTimes(1));
    expect(submitDataset).toHaveBeenCalledWith(DATASET.id);
  });

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

  it('confirms correction after failed validation and prepares again on Start after reset', async () => {
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
    fireEvent.click(await screen.findByRole('button', { name: 'Start preparation' }));
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
    fireEvent.click(await screen.findByRole('button', { name: 'Start preparation' }));
    expect(await screen.findByText('Waiting in queue')).toBeInTheDocument();
    expect(mockSaveNow).toHaveBeenCalledTimes(2);
    expect(submitDataset).toHaveBeenCalledTimes(2);
  });

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
  });

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
      const next = screen.getByRole('button', { name: 'Next' });
      client.setQueryData(depositionKeys.deposition(1), {
        id: 1,
        title: 'Shared deposition',
        authors_json: [],
        datasets: [DATASET, { ...DATASET, id: 6, job: { id: 2, state } }],
      });
      await act(async () => {
        fireEvent.click(screen.getByRole('button', { name: /Step 2: Deposition/ }));
      });
      expect(screen.getByLabelText(/^Title/)).toHaveAttribute('readonly');
      expect(screen.getByText(/Editing is paused because another dataset in this submission/)).toBeInTheDocument();
      await act(async () => {
        fireEvent.click(next);
      });
      expect(screen.getByRole('heading', { name: 'Dataset' })).toBeInTheDocument();
      expect(screen.getByLabelText(/^Title/)).not.toHaveAttribute('readonly');
    }
  );
});
