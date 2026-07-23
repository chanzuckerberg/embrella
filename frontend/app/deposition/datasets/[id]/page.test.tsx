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

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DatasetDetailPage />
    </QueryClientProvider>,
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

  it('renders read-only with a banner for a pushed dataset', () => {
    mockUseDataset.mockReturnValue({ data: PUSHED, isPending: false, isError: false });
    renderPage();
    expect(screen.getByText(/read-only/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/)).toBeDisabled();
  });
});
