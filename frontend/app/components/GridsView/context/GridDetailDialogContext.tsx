'use client';

import { createContext, useContext } from 'react';

interface GridDetailDialogContextValue {
  openGridDetail: (gridId: number) => void;
}

export const GridDetailDialogContext = createContext<GridDetailDialogContextValue>({
  openGridDetail: () => {},
});

export const useGridDetailDialog = () => useContext(GridDetailDialogContext);
