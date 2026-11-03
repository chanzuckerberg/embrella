import { TimelineEntry, TimelineKind } from '@app/common/types/timeline';

// Images arrive in batches (drops, pastes): merge same-kind, same-user entries within this window
const IMAGE_GROUP_WINDOW_MS = 60 * 60 * 1000;

// e.g. "3 images added"; names stay out because pasted screenshots are all "image.png"
const GROUP_VERB: Partial<Record<TimelineKind, string>> = {
  [TimelineKind.IMAGE_ADDED]: 'added',
  [TimelineKind.IMAGE_REMOVED]: 'removed',
};

const canMerge = (group: TimelineEntry, entry: TimelineEntry): boolean =>
  entry.kind in GROUP_VERB &&
  entry.kind === group.kind &&
  entry.user === group.user &&
  entry.subject_id === group.subject_id &&
  Math.abs(new Date(group.at).getTime() - new Date(entry.at).getTime()) <= IMAGE_GROUP_WINDOW_MS;

/**
 * Collapse adjacent image entries into one, e.g.
 * "Image atlas.tif added", "Image image.png added" (same user, 2 min apart) → "2 images added".
 *
 * Only neighbours merge, so an unrelated entry in between keeps the order truthful.
 * Grouped entries carry ``detail.count``; singletons are returned unchanged.
 */
export const groupImages = (entries: TimelineEntry[]): TimelineEntry[] => {
  const out: TimelineEntry[] = [];

  for (const entry of entries) {
    const group = out[out.length - 1];

    if (!group || !canMerge(group, entry)) {
      out.push(entry);
      continue;
    }

    const count = ((group.detail.count as number) ?? 1) + 1;
    out[out.length - 1] = { ...group, summary: `${count} images ${GROUP_VERB[entry.kind]}`, detail: { count } };
  }

  return out;
};
