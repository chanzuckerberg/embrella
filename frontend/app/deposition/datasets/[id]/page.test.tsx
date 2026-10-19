import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';

import DatasetDetailPage from './page';
import { useDataset } from '../../hooks/useDataset';

jest.mock('../../hooks/useDataset', () => ({ useDataset: jest.fn() }));
jest.mock('next/navigation', () => ({ useParams: () => ({ id: '5' }) }));

const mockUseDataset = useDataset as jest.Mock;

const DRAFT = { id: 5, deposition: 1, dataset_id: 100, title: 'My dataset', status: 'draft', funding: [] };
const PUSHED = { ...DRAFT, status: 'pushed' };
const FAILED = { ...DRAFT, status: 'failed', job: { id: 1, state: 'failed' } };

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DatasetDetailPage />
    </QueryClientProvider>
  );
}

describe('DatasetDetailPage', () => {
  it('shows a loader while pending', () => {
    mockUseDataset.mockReturnValue({ data: undefined, isPending: true, isError: false });
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('shows an error when the dataset fails to load', () => {
    mockUseDataset.mockReturnValue({ data: undefined, isPending: false, isError: true });
    renderPage();
    expect(screen.getByText(/could not load this dataset/i)).toBeInTheDocument();
  });

  it('renders an editable form for a draft', () => {
    mockUseDataset.mockReturnValue({ data: DRAFT, isPending: false, isError: false });
    renderPage();
    expect(screen.getByText('ds-100')).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/)).not.toBeDisabled();
    expect(screen.queryByText(/read-only/i)).not.toBeInTheDocument();
  });

  it.each([
    { data: PUSHED, message: /Uploaded datasets can’t be edited/i },
    { data: { ...DRAFT, is_owner: false }, message: /Only the submission owner can edit this dataset/i },
    { data: { ...DRAFT, status: 'syncing' }, message: /Editing is paused during preparation and upload/i },
  ])('renders selectable read-only values for a locked or non-owned dataset', ({ data, message }) => {
    mockUseDataset.mockReturnValue({ data, isPending: false, isError: false });
    renderPage();
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/)).toHaveAttribute('readonly');
    expect(screen.getByLabelText(/Title/)).not.toBeDisabled();
  });

  it('keeps a failed dataset read-only until the owner chooses Edit metadata', () => {
    mockUseDataset.mockReturnValue({ data: FAILED, isPending: false, isError: false });
    renderPage();
    expect(screen.getByLabelText(/Title/)).toHaveAttribute('readonly');
    expect(screen.getByRole('button', { name: 'Edit metadata' })).toBeEnabled();
  });
});
