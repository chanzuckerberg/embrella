import '@testing-library/jest-dom';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { LabelChip, LabelData } from './LabelChip';

const MOCK_LABELS: LabelData[] = [
  { id: 1, name: 'good', color: '#43a047' },
  { id: 2, name: 'bad', color: '#e53935' },
  { id: 3, name: 'ok', color: '#fb8c00' },
  { id: 4, name: 'review', color: '#1e88e5' },
  { id: 5, name: 'priority', color: '#8e24aa' },
  { id: 6, name: 'archived', color: '#757575' },
];

function mockFetch(allLabels: LabelData[] = MOCK_LABELS) {
  global.fetch = jest.fn(async (url: string | URL | Request, init?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString();

    // GET labels list
    if (urlStr.includes('/labels') && (!init || init.method === undefined || init.method === 'GET')) {
      return {
        ok: true,
        status: 200,
        json: async () => allLabels,
      } as Response;
    }

    // PATCH update-labels
    if (urlStr.includes('/update-labels') && init?.method === 'PATCH') {
      return { ok: true, status: 200, json: async () => ({ success: true }) } as Response;
    }

    // POST create label
    if (urlStr.includes('/labels') && init?.method === 'POST') {
      const body = JSON.parse(init.body as string);
      const newLabel: LabelData = { id: 99, name: body.name, color: '#546e7a' };
      return { ok: true, status: 201, json: async () => newLabel } as Response;
    }

    return { ok: false, status: 404 } as Response;
  });
}

beforeEach(() => {
  mockFetch();
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('LabelChip', () => {
  describe('view mode', () => {
    it('renders label chips when labels exist', () => {
      const labels = [MOCK_LABELS[0], MOCK_LABELS[1]];
      render(<LabelChip gridId={1} labels={labels} />);
      expect(screen.getByText('good')).toBeInTheDocument();
      expect(screen.getByText('bad')).toBeInTheDocument();
    });

    it('renders "+ Add" chip when no labels', () => {
      render(<LabelChip gridId={1} labels={[]} />);
      expect(screen.getByText('+ Add')).toBeInTheDocument();
    });

    it('enters edit mode on click', async () => {
      render(<LabelChip gridId={1} labels={[]} />);
      await act(async () => {
        fireEvent.click(screen.getByText('+ Add'));
      });
      expect(screen.getByPlaceholderText('Type label...')).toBeInTheDocument();
    });
  });

  describe('edit mode', () => {
    it('shows suggestions when editing with empty input', async () => {
      render(<LabelChip gridId={1} labels={[]} />);

      await act(async () => {
        fireEvent.click(screen.getByText('+ Add'));
      });

      // Wait for labels to be fetched and suggestions to appear
      await waitFor(() => {
        // Should show top 5 available labels
        expect(screen.getByText('good')).toBeInTheDocument();
      });
    });

    it('filters suggestions based on input', async () => {
      render(<LabelChip gridId={1} labels={[]} />);

      await act(async () => {
        fireEvent.click(screen.getByText('+ Add'));
      });

      // Wait for labels fetch
      await waitFor(() => {
        expect(screen.getByText('good')).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText('Type label...');
      await act(async () => {
        fireEvent.change(input, { target: { value: 'go' } });
      });

      await waitFor(() => {
        expect(screen.getByText('good')).toBeInTheDocument();
        expect(screen.queryByText('bad')).not.toBeInTheDocument();
      });
    });

    it('adds a label on click', async () => {
      render(<LabelChip gridId={1} labels={[]} />);

      await act(async () => {
        fireEvent.click(screen.getByText('+ Add'));
      });

      await waitFor(() => {
        expect(screen.getByText('good')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByText('good'));
      });

      // Label should now be shown as a chip (with delete button in edit mode)
      expect(screen.getByText('good')).toBeInTheDocument();

      // Verify PATCH was called
      const patchCalls = (fetch as jest.Mock).mock.calls.filter(
        ([, init]: [string, RequestInit | undefined]) => init?.method === 'PATCH'
      );
      expect(patchCalls.length).toBe(1);
      const body = JSON.parse(patchCalls[0][1].body);
      expect(body.label_ids).toContain(MOCK_LABELS[0].id);
    });

    it('excludes already-selected labels from suggestions', async () => {
      const selected = [MOCK_LABELS[0]]; // "good" already selected
      render(<LabelChip gridId={1} labels={selected} />);

      await act(async () => {
        fireEvent.click(screen.getByText('good'));
      });

      await waitFor(() => {
        // "good" should not appear in suggestions since it's already selected
        // but it should be in the chips area
        const suggestions = screen.queryAllByText('good');
        // Only one instance — the chip, not a suggestion
        expect(suggestions.length).toBe(1);
      });
    });

    it('creates new label on Enter when no match', async () => {
      render(<LabelChip gridId={1} labels={[]} />);

      await act(async () => {
        fireEvent.click(screen.getByText('+ Add'));
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Type label...')).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText('Type label...');
      await act(async () => {
        fireEvent.change(input, { target: { value: 'newlabel' } });
      });

      // Wait for debounce
      await waitFor(() => {
        // No suggestion should match "newlabel"
        expect(screen.queryByText('newlabel')).toBeNull();
      });

      await act(async () => {
        fireEvent.keyDown(input, { key: 'Enter' });
      });

      // Verify POST was called to create the label
      const postCalls = (fetch as jest.Mock).mock.calls.filter(
        ([, init]: [string, RequestInit | undefined]) => init?.method === 'POST'
      );
      expect(postCalls.length).toBe(1);
      const body = JSON.parse(postCalls[0][1].body);
      expect(body.name).toBe('newlabel');
    });

    it('closes edit mode on Escape', async () => {
      render(<LabelChip gridId={1} labels={[]} />);

      await act(async () => {
        fireEvent.click(screen.getByText('+ Add'));
      });

      const input = screen.getByPlaceholderText('Type label...');
      await act(async () => {
        fireEvent.keyDown(input, { key: 'Escape' });
      });

      expect(screen.queryByPlaceholderText('Type label...')).not.toBeInTheDocument();
    });
  });
});
