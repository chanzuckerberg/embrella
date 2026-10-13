import { useCallback, useEffect } from 'react';
import { parseAsString, useQueryState } from 'nuqs';
import { ReviewTomogramSummary } from '../types';

/** Deep-link key, e.g. `/processing/tomograms/reviews/<id>?position=Position_12`. */
const POSITION_PARAM = 'position';

const positionParser = parseAsString.withOptions({ history: 'replace' });

/**
 * URL-backed tomogram selection. `?position=` is the source of truth; a missing or
 * unknown position falls back to the first tomogram and is written back so the
 * address bar is always shareable.
 */
export const useSelectedTomogram = (tomograms: ReviewTomogramSummary[]) => {
  const [position, setPosition] = useQueryState(POSITION_PARAM, positionParser);

  const selected = tomograms.find((t) => t.position === position) ?? tomograms[0];

  // Normalize URL to the resolved tomogram
  useEffect(() => {
    if (!selected || selected.position === position) return;
    setPosition(selected.position);
  }, [selected, position, setPosition]);

  const selectTomogram = useCallback(
    (tomogramId: string) => {
      const target = tomograms.find((t) => t.tomogramId === tomogramId);
      if (!target) return;
      setPosition(target.position);
    },
    [tomograms, setPosition]
  );

  return { selectedTomogramId: selected?.tomogramId ?? '', selectTomogram };
};
