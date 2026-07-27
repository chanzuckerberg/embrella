import '@testing-library/jest-dom';
import { fireEvent, render, screen } from '@testing-library/react';

import SubmissionsPage from './page';
import { useSubmissions } from '../hooks/useSubmissions';

jest.mock('../hooks/useSubmissions', () => ({ useSubmissions: jest.fn() }));
const mockUseSubmissions = useSubmissions as jest.Mock;

const DATASETS = [
  {
    id: 1,
    dataset_id: 100,
    title: 'A',
    status: 'pushed',
    type: 'Tomos only',
    session_names: [],
    session_count: 0,
    updated_at: '2026-07-01T00:00:00Z',
  },
  {
    id: 2,
    dataset_id: 101,
    title: 'B',
    status: 'pushed',
    type: 'Dataset',
    session_names: ['s1'],
    session_count: 1,
    updated_at: '2026-07-01T00:00:00Z',
  },
  {
    id: 3,
    dataset_id: 102,
    title: 'C',
    status: 'draft',
    type: 'Annotations only',
    session_names: ['s2'],
    session_count: 1,
    updated_at: '2026-07-01T00:00:00Z',
  },
];
const SUBMISSIONS = [{ id: 1, deposition_id: 10001, title: 'Test dep', datasets: DATASETS }];

const ORDER_DATASETS = [
  {
    id: 1,
    dataset_id: 100,
    title: 'Alpha',
    status: 'pushed',
    type: 'Tomos only',
    session_names: [],
    session_count: 0,
    updated_at: '2026-07-01T00:00:00Z',
  },
  {
    id: 2,
    dataset_id: 102,
    title: 'Gamma',
    status: 'draft',
    type: 'Tomos only',
    session_names: [],
    session_count: 0,
    updated_at: '2026-07-05T00:00:00Z',
  },
  {
    id: 3,
    dataset_id: 101,
    title: 'Beta',
    status: 'pushed',
    type: 'Tomos only',
    session_names: [],
    session_count: 0,
    updated_at: '2026-07-03T00:00:00Z',
  },
];
const ORDER_SUBMISSIONS = [{ id: 1, deposition_id: 10001, title: 'Test dep', datasets: ORDER_DATASETS }];

const dsLabels = () => screen.getAllByText(/^ds-\d+$/).map((el) => el.textContent);

describe('SubmissionsPage', () => {
  it('shows the empty state when there are no submissions', () => {
    mockUseSubmissions.mockReturnValue({ data: { submissions: [], total_count: 0 }, isPending: false, isError: false });
    render(<SubmissionsPage />);
    expect(screen.getByText('No submissions yet.')).toBeInTheDocument();
  });

  it('shows a loader while pending', () => {
    mockUseSubmissions.mockReturnValue({ data: undefined, isPending: true, isError: false });
    render(<SubmissionsPage />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('shows an error message on failure', () => {
    mockUseSubmissions.mockReturnValue({ data: undefined, isPending: false, isError: true });
    render(<SubmissionsPage />);
    expect(screen.getByText(/Failed to load submissions/i)).toBeInTheDocument();
  });

  it('renders each dataset type and the deposition group', () => {
    mockUseSubmissions.mockReturnValue({
      data: { submissions: SUBMISSIONS, total_count: 1 },
      isPending: false,
      isError: false,
    });
    render(<SubmissionsPage />);
    expect(screen.getByText('Tomos only')).toBeInTheDocument();
    expect(screen.getByText('Annotations only')).toBeInTheDocument();
    // "Dataset" appears as both the column header and the type chip → expect ≥ 2
    expect(screen.getAllByText('Dataset').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Deposition cdp-10001/)).toBeInTheDocument();
  });

  it('filters rows by search (dataset id)', () => {
    mockUseSubmissions.mockReturnValue({
      data: { submissions: SUBMISSIONS, total_count: 1 },
      isPending: false,
      isError: false,
    });
    render(<SubmissionsPage />);
    fireEvent.change(screen.getByPlaceholderText('Search datasets or depositions'), { target: { value: '102' } });
    expect(screen.getByText('ds-102')).toBeInTheDocument();
    expect(screen.queryByText('ds-100')).not.toBeInTheDocument();
  });

  it('keeps all a deposition’s datasets when the search matches the deposition', () => {
    mockUseSubmissions.mockReturnValue({
      data: { submissions: SUBMISSIONS, total_count: 1 },
      isPending: false,
      isError: false,
    });
    render(<SubmissionsPage />);
    fireEvent.change(screen.getByPlaceholderText('Search datasets or depositions'), { target: { value: 'Test dep' } });
    expect(dsLabels()).toEqual(['ds-100', 'ds-101', 'ds-102']);
  });

  it('reorders rows when sorting by Dataset ID', () => {
    mockUseSubmissions.mockReturnValue({
      data: { submissions: ORDER_SUBMISSIONS, total_count: 1 },
      isPending: false,
      isError: false,
    });
    render(<SubmissionsPage />);
    // Default sort is "recently updated" → newest first.
    expect(dsLabels()).toEqual(['ds-102', 'ds-101', 'ds-100']);
    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(screen.getByRole('option', { name: 'Dataset ID' }));
    expect(dsLabels()).toEqual(['ds-100', 'ds-101', 'ds-102']);
  });
});
