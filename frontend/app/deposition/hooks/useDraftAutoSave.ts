import { useCallback, useEffect, useRef, useState } from 'react';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export interface AutoSaveState {
  status: SaveStatus;
  lastSavedAt: Date | null;
  saveNow: () => void;
}

const DEFAULT_DEBOUNCE_MS = 5000;

interface Options {
  debounceMs?: number;
  enabled?: boolean; // skip while there's no draft yet (e.g. no id)
}

/**
 * autosave for a draft form.
 * Returns { status, lastSavedAt, saveNow }. Call `saveNow()` to flush immediately.
 */
export function useDraftAutoSave<T>(
  data: T,
  save: (data: T) => Promise<unknown>,
  { debounceMs = DEFAULT_DEBOUNCE_MS, enabled = true }: Options = {},
) {
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstRun = useRef(true);
  // Keep the latest data/save without re-arming the debounce on identity changes.
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
    // Don't autosave the data we just loaded into the form.
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

  return { status, lastSavedAt, saveNow: flush };
}
