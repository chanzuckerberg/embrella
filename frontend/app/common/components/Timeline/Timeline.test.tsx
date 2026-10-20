import { render, screen } from '@testing-library/react';
import { Timeline } from './Timeline';
import { TimelineEntry, TimelineKind, TimelineSubject } from '@app/common/types/timeline';

const entry = (overrides: Partial<TimelineEntry>): TimelineEntry => ({
  at: '2024-01-01T12:00:00Z',
  subject: TimelineSubject.GRID,
  subject_id: 1,
  kind: TimelineKind.CREATED,
  summary: 'Grid created',
  user: 'jdoe',
  detail: {},
  ...overrides,
});

describe('Timeline', () => {
  it('shows the empty text without entries', () => {
    render(<Timeline entries={[]} />);

    expect(screen.getByText('No history yet.')).toBeInTheDocument();
  });

  it('renders summary, user and relative time', () => {
    render(<Timeline entries={[entry({ kind: TimelineKind.MOVED, summary: 'Moved from BoxA #1 to BoxB #2' })]} />);

    expect(screen.getByText('Moved from BoxA #1 to BoxB #2')).toBeInTheDocument();
    expect(screen.getByText('jdoe')).toBeInTheDocument();
    expect(screen.getByText(/ago$/)).toBeInTheDocument();
  });

  it('shows a scroll hint only when capped', () => {
    const entries = Array.from({ length: 3 }, (_, i) => entry({ subject_id: i }));
    const { rerender } = render(<Timeline entries={entries} maxVisible={2} />);

    expect(screen.getByText('3 entries · scroll for more')).toBeInTheDocument();

    rerender(<Timeline entries={entries} maxVisible={8} />);
    expect(screen.queryByText(/scroll for more/)).not.toBeInTheDocument();
  });

  it('groups rows under day headers, newest first', () => {
    render(
      <Timeline
        entries={[
          entry({ at: new Date().toISOString(), summary: 'Moved', kind: TimelineKind.MOVED }),
          entry({ at: '2024-01-02T12:00:00', summary: 'Clipped', kind: TimelineKind.CLIPPED }),
          entry({ at: '2024-01-02T09:00:00', summary: 'Edited', kind: TimelineKind.EDITED }),
          entry({ at: '2024-01-01T12:00:00' }),
        ]}
      />
    );

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getAllByText('Jan 2 2024')).toHaveLength(1);
    expect(screen.getByText('Jan 1 2024')).toBeInTheDocument();
  });

  it('uses a container icon when the grid moved inside its box / puck / cane / dewar', () => {
    render(
      <Timeline
        entries={[
          entry({ kind: TimelineKind.MOVED, summary: 'Box BoxA moved to PuckB #3', detail: { via: 'box' } }),
          entry({ kind: TimelineKind.MOVED, summary: 'Moved from BoxA #1 to BoxB #2' }),
        ]}
      />
    );

    expect(screen.getAllByTestId('Inventory2OutlinedIcon')).toHaveLength(1);
    expect(screen.getAllByTestId('DriveFileMoveOutlinedIcon')).toHaveLength(1);
  });

  it('tags non-grid subjects', () => {
    render(
      <Timeline
        entries={[
          entry({ subject: TimelineSubject.MSI_SESSION, summary: 'MSI session 24nov10 created' }),
          entry({ subject: TimelineSubject.PROC_RUN, summary: 'Proc run run001 created', user: null }),
          entry({}),
        ]}
      />
    );

    expect(screen.getByText('MSI Session')).toBeInTheDocument();
    expect(screen.getByText('Proc Run')).toBeInTheDocument();
    expect(screen.queryByText('Grid')).not.toBeInTheDocument();
  });
});
