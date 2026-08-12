import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { SessionOverviewData, SessionRunRow } from '../types';
import { SessionSoftwareSubRow } from './SessionSoftwareSubRow';

const makeRun = (overrides: Partial<SessionRunRow> & Pick<SessionRunRow, 'id'>): SessionRunRow => ({
  run: { id: 1, name: 'run001' },
  planName: 'czii-live',
  planLabel: 'aretomo3',
  createdAt: '2026-08-01T09:00:00-07:00',
  ...overrides,
});

const makeSession = (runs: SessionRunRow[]): SessionOverviewData => ({
  session: { id: 42, name: '24mar01a' },
  sessionDate: '2026-07-01T09:00:00-07:00',
  user: null,
  project: null,
  scope: 'krios1',
  workflow: 'tomo',
  grid: null,
  runCount: runs.length,
  processingSoftware: [],
  reviewCount: 0,
  lastRunAt: null,
  runs,
});

const twoSoftwares = makeSession([
  makeRun({ id: 'run-3', run: { id: 3, name: 'run003' }, createdAt: '2026-08-05T09:00:00-07:00' }),
  makeRun({ id: 'run-2', run: { id: 2, name: 'run002' }, planLabel: 'denoise', planName: 'czii-denoise' }),
  makeRun({ id: 'run-1', run: { id: 1, name: 'run001' } }),
]);

describe('SessionSoftwareSubRow', () => {
  it('renders one row per software display name with its run count', () => {
    render(<SessionSoftwareSubRow data={twoSoftwares} />);

    expect(screen.getByText('aretomo3')).toBeInTheDocument();
    expect(screen.getByText('2 runs')).toBeInTheDocument();
    expect(screen.getByText('denoise')).toBeInTheDocument();
    expect(screen.getByText('1 run')).toBeInTheDocument();
  });

  it('keeps runs hidden until the software row is expanded', async () => {
    render(<SessionSoftwareSubRow data={twoSoftwares} />);

    expect(screen.queryByText('run003')).not.toBeInTheDocument();

    await userEvent.click(screen.getAllByRole('button', { name: 'Expand runs' })[0]);

    expect(screen.getByText('run003')).toBeInTheDocument();
    expect(screen.getByText('run001')).toBeInTheDocument();
    // Only this software's runs — the denoise run stays collapsed.
    expect(screen.queryByText('run002')).not.toBeInTheDocument();
  });

  it('shows the machine plan key alongside the display label', async () => {
    render(<SessionSoftwareSubRow data={twoSoftwares} />);
    await userEvent.click(screen.getAllByRole('button', { name: 'Expand runs' })[0]);

    expect(screen.getAllByText('czii-live')).toHaveLength(2);
  });

  it('lists the newest run first within a software', async () => {
    render(<SessionSoftwareSubRow data={twoSoftwares} />);
    await userEvent.click(screen.getAllByRole('button', { name: 'Expand runs' })[0]);

    const runNames = screen.getAllByText(/^run00\d$/).map((cell) => cell.textContent);

    expect(runNames).toEqual(['run003', 'run001']);
  });

  it('collapses again on a second click', async () => {
    render(<SessionSoftwareSubRow data={twoSoftwares} />);

    await userEvent.click(screen.getAllByRole('button', { name: 'Expand runs' })[0]);
    expect(screen.getByText('run003')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Collapse runs' }));
    expect(screen.queryByText('run003')).not.toBeInTheDocument();
  });

  it('explains itself when a session has no runs', () => {
    render(<SessionSoftwareSubRow data={makeSession([])} />);
    expect(screen.getByText('No processing runs for this session')).toBeInTheDocument();
  });
});
