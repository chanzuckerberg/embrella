import { useCallback, useEffect, useRef, useState } from 'react';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export interface AutoSaveState {
  status: SaveStatus;
  lastSavedAt: Date | null;
  saveNow: () => Promise<void>;
}

const DEFAULT_DEBOUNCE_MS = 5000;

interface Options {
  debounceMs?: number;
  enabled?: boolean; // skip while there's no draft yet (e.g. no id)
}

/** Draft autosave. Returns { status, lastSavedAt, saveNow }. */
export function useDraftAutoSave<T>(
  data: T,
  save: (data: T) => Promise<unknown>,
  { debounceMs = DEFAULT_DEBOUNCE_MS, enabled = true }: Options = {},
) {
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstRun = useRef(true);
  const dataRef = useRef(data);
  const saveRef = useRef(save);
  useEffect(() => {
    dataRef.current = data;
    saveRef.current = save;
  });

  const flush = useCallback(async () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    setStatus('saving');
    try {
      await saveRef.current(dataRef.current);
      setStatus('saved');
      setLastSavedAt(new Date());
    } catch {
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    if (isFirstRun.current) {
      isFirstRun.current = false;
      return undefined;
    }

    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(flush, debounceMs);

    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [data, enabled, debounceMs, flush]);
  // Flush pending save on unmount so step/exit navigation doesn't drop edits.
  useEffect(() => {
    return () => {
      if (timer.current) {
        clearTimeout(timer.current);
        timer.current = null;
        saveRef.current(dataRef.current).catch(() => {});
      }
    };
  }, []);

  return { status, lastSavedAt, saveNow: flush };
}
