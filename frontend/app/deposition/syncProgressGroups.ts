import type { SyncChecklistItem } from './types';

const SYNC_PROGRESS_GROUPS = [
  { label: 'Symlink tiltseries', categories: ['Tilt series', 'Alignment', 'CTF'] },
  { label: 'Symlink tomograms', categories: ['Tomograms'] },
  { label: 'Deposit annotations', categories: ['Annotations'] },
  { label: 'Other items', categories: ['Masks', 'Metadata', 'Frames'] },
] as const;

// Combine category counts into the displayed rows.
export function groupSyncProgress(items: readonly SyncChecklistItem[]): SyncChecklistItem[] {
  const groups = SYNC_PROGRESS_GROUPS.map(({ label }) => ({ label, done: 0, total: 0 }));
  for (const item of items) {
    const index = SYNC_PROGRESS_GROUPS.findIndex((group) => group.categories.some((label) => label === item.label));
    // The backend currently filters unknown labels. Keep a fallback for future API additions.
    const group = groups[index === -1 ? groups.length - 1 : index];
    group.done += item.done;
    group.total += item.total;
  }
  return groups.filter((group) => group.total > 0);
}
