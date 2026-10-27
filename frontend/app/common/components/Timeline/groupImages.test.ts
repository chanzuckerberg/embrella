import { groupImages } from './groupImages';
import { TimelineEntry, TimelineKind, TimelineSubject } from '@app/common/types/timeline';

const image = (name: string, at: string, overrides: Partial<TimelineEntry> = {}): TimelineEntry => ({
  at,
  subject: TimelineSubject.GRID,
  subject_id: 1,
  kind: TimelineKind.IMAGE_ADDED,
  summary: `Image ${name} added`,
  user: 'jdoe',
  detail: { image_id: name, name },
  ...overrides,
});

describe('groupImages', () => {
  it('counts a batch within the hour', () => {
    const [group] = groupImages([
      image('a.png', '2024-01-01T12:30:00Z'),
      image('b.png', '2024-01-01T12:10:00Z'),
      image('c.png', '2024-01-01T12:00:00Z'),
    ]);

    expect(group.summary).toBe('3 images added');
    expect(group.at).toBe('2024-01-01T12:30:00Z');
  });

  it('keeps a single image as is', () => {
    const [entry] = groupImages([image('atlas.tif', '2024-01-01T12:00:00Z')]);

    expect(entry.summary).toBe('Image atlas.tif added');
  });

  it('does not merge different users, kinds or far-apart entries', () => {
    const entries = [
      image('a.png', '2024-01-01T15:00:00Z'),
      image('b.png', '2024-01-01T12:02:00Z'),
      image('c.png', '2024-01-01T12:01:00Z', { user: 'other' }),
      image('d.png', '2024-01-01T12:00:00Z', { user: 'other', kind: TimelineKind.IMAGE_REMOVED }),
    ];

    expect(groupImages(entries)).toHaveLength(4);
  });

  it('leaves label entries to groupLabels', () => {
    const label = image('', '2024-01-01T12:01:00Z', { kind: TimelineKind.LABEL_ADDED, summary: 'Label P1 added' });

    expect(groupImages([label, { ...label, at: '2024-01-01T12:00:00Z' }])).toHaveLength(2);
  });
});
