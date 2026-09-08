import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SessionDetails } from './SessionDetails';

const SESSION = {
  id: 7,
  name: 'p52sep01a',
  project_name: 'serialem-testing',
  grid_name: 'default grid.c1',
  session_plan_name: 'TEM Tomography collected with serialEM on krios2 and GatanCeltic',
  magnification_display: null,
  frames: { directory: '/hpc/instruments/czii.krios2.k3/p52sep01a/', pattern: '*.tif' },
  sums: { directory: null, pattern: null },
  mdocs: { directory: '/hpc/instruments/czii.krios2.k3/p52sep01a/', pattern: '*.mrc.mdoc' },
  parents: { directory: null, pattern: null },
  atlas: { directory: null, pattern: null },
  legacy_url: '/legacy/tem/7/',
};

beforeEach(() => {
  global.fetch = jest.fn(async (url: string | URL | Request) => {
    const ok = url.toString().endsWith('/tem/v1/sessions/p52sep01a/');
    return { ok, status: ok ? 200 : 404, json: async () => SESSION } as Response;
  });
});

describe('SessionDetails', () => {
  it('shows the plan in the summary and the dialog content when expanded', async () => {
    render(<SessionDetails sessionName="p52sep01a" />);

    // Plan name appears twice once loaded: header subtitle and the Session Plan row
    await waitFor(() => expect(screen.getAllByText(SESSION.session_plan_name)).toHaveLength(2));

    fireEvent.click(screen.getByText('Session details'));

    const panel = screen.getByTestId('session-details');
    expect(panel).toHaveTextContent('Project:serialem-testing');
    expect(panel).toHaveTextContent('Frames'); // uppercased by CSS, not in text content
    expect(panel).toHaveTextContent('files: *.tif');
    expect(panel).not.toHaveTextContent('Please review');
  });

  it('reports a failed fetch', async () => {
    render(<SessionDetails sessionName="missing" />);

    await waitFor(() => expect(screen.getByText('Could not load session details.')).toBeInTheDocument());
  });
});
