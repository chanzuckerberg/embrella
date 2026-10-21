import { groupSyncProgress } from './syncProgressGroups';
import type { SyncChecklistItem } from './types';

it('sums categories in display order without mutating the snapshot', () => {
  const items: SyncChecklistItem[] = [
    { label: 'Frames', done: 2, total: 5 },
    { label: 'Tomograms', done: 3, total: 4 },
    { label: 'CTF', done: 1, total: 2 },
    { label: 'Masks', done: 1, total: 1 },
    { label: 'Tilt series', done: 2, total: 4 },
    { label: 'Metadata', done: 2, total: 3 },
    { label: 'Alignment', done: 2, total: 2 },
  ];
  const before = JSON.stringify(items);
  expect(groupSyncProgress(items)).toEqual([
    { label: 'Symlink tiltseries', done: 5, total: 8 },
    { label: 'Symlink tomograms', done: 3, total: 4 },
    { label: 'Other items', done: 5, total: 9 },
  ]);
  expect(JSON.stringify(items)).toBe(before);
});

it('hides all groups without a positive total, including annotations', () => {
  expect(groupSyncProgress([])).toEqual([]);
  expect(
    groupSyncProgress([
      { label: 'Tilt series', done: 0, total: 0 },
      { label: 'Tomograms', done: 0, total: 0 },
      { label: 'Metadata', done: 0, total: 0 },
    ])
  ).toEqual([]);
});

it('adds unknown categories to Other items alongside known categories', () => {
  expect(
    groupSyncProgress([
      { label: 'Future category', done: 1, total: 4 },
      { label: 'Metadata', done: 2, total: 3 },
    ])
  ).toEqual([{ label: 'Other items', done: 3, total: 7 }]);
});
