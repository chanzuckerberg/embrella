import { TimelineEntry, TimelineKind } from '@app/common/types/timeline';

// Labels are usually applied in batches: merge same-kind, same-user entries within this window
const LABEL_GROUP_WINDOW_MS = 60 * 60 * 1000;

export const LABEL_GROUP_TITLE: Partial<Record<TimelineKind, string>> = {
  [TimelineKind.LABEL_ADDED]: 'Labels added',
  [TimelineKind.LABEL_REMOVED]: 'Labels removed',
};

export interface TimelineLabel {
  label: string | null;
  color: string | null;
}

const labelOf = (entry: TimelineEntry): TimelineLabel => ({
  label: (entry.detail.label as string | null) ?? null,
  color: (entry.detail.color as string | null) ?? null,
});

const canMerge = (group: TimelineEntry, entry: TimelineEntry): boolean =>
  entry.kind in LABEL_GROUP_TITLE &&
  entry.kind === group.kind &&
  entry.user === group.user &&
  entry.subject_id === group.subject_id &&
  Math.abs(new Date(group.at).getTime() - new Date(entry.at).getTime()) <= LABEL_GROUP_WINDOW_MS;

/**
 * Collapse adjacent label entries into one, e.g.
 * "Label TBS added", "Label P1 added" (same user, 5 min apart) → "Labels added: TBS, P1".
 *
 * Only neighbours merge, so an unrelated entry in between keeps the order truthful.
 * Grouped entries carry ``detail.labels``; singletons are returned unchanged.
 */
export const groupLabels = (entries: TimelineEntry[]): TimelineEntry[] => {
  const out: TimelineEntry[] = [];

  for (const entry of entries) {
    const group = out[out.length - 1];

    if (!group || !canMerge(group, entry)) {
      out.push(entry);
      continue;
    }

    const labels = [...((group.detail.labels as TimelineLabel[]) ?? [labelOf(group)]), labelOf(entry)];
    out[out.length - 1] = {
      ...group,
      summary: `${LABEL_GROUP_TITLE[entry.kind]}: ${labels.map((l) => l.label ?? 'unknown').join(', ')}`,
      detail: { labels },
    };
  }

  return out;
};
