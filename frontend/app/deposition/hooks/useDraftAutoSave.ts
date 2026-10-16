import { useCallback, useEffect, useRef, useState } from 'react';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export interface AutoSaveState {
  status: SaveStatus;
  isDirty: boolean;
  lastSavedAt: Date | null;
  // true on success (or nothing to save), false on failure. Callers hold navigation on false.
  saveNow: () => Promise<boolean>;
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
      try {
        // Replay if the user edited while this save was in flight.
        while (savedRevision.current < revision.current) {
          const targetRevision = revision.current;
          const snapshot = dataRef.current;
          await saveRef.current(snapshot);
          savedRevision.current = targetRevision;
        }
        setIsDirty(false);
        setStatus('saved');
        setLastSavedAt(new Date());
        return true;
      } catch {
        setStatus('error');
        return false;
      } finally {
        inFlight.current = null;
      }
    })();
    inFlight.current = run;
    return run;
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
    if (!enabled || !isDirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [enabled, isDirty]);

  return { status, isDirty, lastSavedAt, saveNow: flush };
}
