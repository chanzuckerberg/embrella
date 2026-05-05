'use client';

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import { ScreeningLabel } from '@app/components/Screening/types';

interface ScreeningLabelsContextValue {
  getLabels: (gridId: number, fallback: ScreeningLabel[]) => ScreeningLabel[];
  setLabels: (gridId: number, labels: ScreeningLabel[]) => void;
}

const ScreeningLabelsContext = createContext<ScreeningLabelsContextValue>({
  getLabels: (_gridId, fallback) => fallback,
  setLabels: () => {},
});

export const ScreeningLabelsProvider = ({ children }: { children: React.ReactNode }) => {
  const [overrides, setOverrides] = useState<Record<number, ScreeningLabel[]>>({});

  const getLabels = useCallback(
    (gridId: number, fallback: ScreeningLabel[]) => overrides[gridId] ?? fallback,
    [overrides]
  );

  const setLabels = useCallback((gridId: number, labels: ScreeningLabel[]) => {
    setOverrides((prev) => ({ ...prev, [gridId]: labels }));
  }, []);

  const value = useMemo(() => ({ getLabels, setLabels }), [getLabels, setLabels]);

  return <ScreeningLabelsContext.Provider value={value}>{children}</ScreeningLabelsContext.Provider>;
};

export const useScreeningLabels = () => useContext(ScreeningLabelsContext);
