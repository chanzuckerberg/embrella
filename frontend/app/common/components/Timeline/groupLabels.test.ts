import { groupLabels } from './groupLabels';
import { TimelineEntry, TimelineKind, TimelineSubject } from '@app/common/types/timeline';

const label = (name: string, at: string, overrides: Partial<TimelineEntry> = {}): TimelineEntry => ({
  at,
  subject: TimelineSubject.GRID,
  subject_id: 1,
  kind: TimelineKind.LABEL_ADDED,
  summary: `Label ${name} added`,
  user: 'jdoe',
  detail: { label: name, color: '#43a047' },
  ...overrides,
});

describe('groupLabels', () => {
  it('merges a batch within the hour', () => {
    const [group] = groupLabels([label('TBS', '2024-01-01T12:30:00Z'), label('P1', '2024-01-01T12:00:00Z')]);

    expect(group.summary).toBe('Labels added: TBS, P1');
    expect(group.at).toBe('2024-01-01T12:30:00Z');
  });

  it('keeps entries more than an hour apart', () => {
    expect(groupLabels([label('TBS', '2024-01-01T14:00:00Z'), label('P1', '2024-01-01T12:00:00Z')])).toHaveLength(2);
  });

  it('does not merge different users or kinds', () => {
    const entries = [
      label('TBS', '2024-01-01T12:02:00Z'),
      label('P1', '2024-01-01T12:01:00Z', { user: 'other' }),
      label('P2', '2024-01-01T12:00:00Z', { user: 'other', kind: TimelineKind.LABEL_REMOVED }),
    ];

    expect(groupLabels(entries)).toHaveLength(3);
  });

  it('does not merge across an unrelated entry', () => {
    const move = label('', '2024-01-01T12:01:00Z', { kind: TimelineKind.MOVED, summary: 'Moved', detail: {} });

    expect(groupLabels([label('TBS', '2024-01-01T12:02:00Z'), move, label('P1', '2024-01-01T12:00:00Z')])).toHaveLength(
      3
    );
  });
});
