// Mirrors the backend timeline API (umbrella/timeline/types.py)

export enum TimelineSubject {
  GRID = 'grid',
  MSI_SESSION = 'msi_session',
  PROC_RUN = 'proc_run',
}

export enum TimelineKind {
  CREATED = 'created',
  EDITED = 'edited',
  MOVED = 'moved',
  TRASHED = 'trashed',
  RESTORED = 'restored',
  CLIPPED = 'clipped',
  UNCLIPPED = 'unclipped',
  LABEL_ADDED = 'label_added',
  LABEL_REMOVED = 'label_removed',
  IMAGE_ADDED = 'image_added',
  IMAGE_REMOVED = 'image_removed',
  DELETED = 'deleted',
}

export interface TimelineEntry {
  at: string;
  subject: TimelineSubject;
  subject_id: number;
  kind: TimelineKind;
  summary: string;
  user: string | null;
  // Kind-specific extras, e.g. { label, color } for label entries
  detail: Record<string, unknown>;
}
