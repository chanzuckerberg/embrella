import { useCallback, useEffect, useRef, useState } from 'react';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export interface AutoSaveState {
  status: SaveStatus;
  // Unsaved edits remain dirty after a save error or a metadata lock, until saved or discarded.
  isDirty: boolean;
  lastSavedAt: Date | null;
  error?: string | null;
  // true on success (or nothing to save), false on failure. Callers hold navigation on false.
  saveNow: () => Promise<boolean>;
  discardChanges: () => void;
}

const DEFAULT_DEBOUNCE_MS = 5000;

interface Options {
  debounceMs?: number;
  enabled?: boolean; // skip while there's no draft yet (e.g. no id)
}

export function useDraftAutoSave<T>(
  data: T,
  save: (data: T) => Promise<unknown>,
  { debounceMs = DEFAULT_DEBOUNCE_MS, enabled = true }: Options = {}
) {
  const [isDirty, setIsDirty] = useState(false);
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const observedData = useRef(data);
  const dataRef = useRef(data);
  const saveRef = useRef(save);
  const revision = useRef(0);
  const savedRevision = useRef(0);
  const inFlight = useRef<Promise<boolean> | null>(null);
  useEffect(() => {
    dataRef.current = data;
    saveRef.current = save;
  });

  const flush = useCallback(async (): Promise<boolean> => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (inFlight.current) return inFlight.current;
    if (savedRevision.current === revision.current) return true;

    const run = (async () => {
      setStatus('saving');
      setError(null);
      try {
        // Replay if the user edited while this save was in flight.
        while (savedRevision.current < revision.current) {
          const targetRevision = revision.current;
          const snapshot = dataRef.current;
          await saveRef.current(snapshot);
          savedRevision.current = Math.max(savedRevision.current, targetRevision);
        }
        setIsDirty(false);
        setStatus('saved');
        setLastSavedAt(new Date());
        return true;
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'Your changes could not be saved. Please try again.');
        setStatus('error');
        return false;
      } finally {
        inFlight.current = null;
      }
    })();
    inFlight.current = run;
    return run;
  }, []);

  const discardChanges = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    // Prevent the unmount cleanup from saving edits the user explicitly discarded.
    savedRevision.current = revision.current;
    setIsDirty(false);
    setStatus('idle');
    setError(null);
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    if (!Object.is(observedData.current, data)) {
      observedData.current = data;
      revision.current += 1;
      setIsDirty(true);
    }
    if (savedRevision.current === revision.current) return undefined;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(flush, debounceMs);

    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [data, enabled, debounceMs, flush]);
  useEffect(() => {
    return () => {
      if (timer.current) {
        clearTimeout(timer.current);
        timer.current = null;
      }
      if (savedRevision.current < revision.current && !inFlight.current) {
        saveRef.current(dataRef.current).catch(() => {});
      }
    };
  }, []);

  useEffect(() => {
    if (!isDirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [isDirty]);

  return { status, isDirty, lastSavedAt, error, saveNow: flush, discardChanges };
}
