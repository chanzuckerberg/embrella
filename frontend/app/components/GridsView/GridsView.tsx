'use client';

import React, { Suspense, useCallback, useMemo } from 'react';
import { parseAsInteger, useQueryState } from 'nuqs';
import { CircularProgress } from '@mui/material';
import { GRID_COLUMN_DEFS } from './constants/columns';
import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { API } from '@app/common/constants/api';
import { GridDetailDialogContext } from './context/GridDetailDialogContext';

const GridDetailDialog = React.lazy(() =>
  import('@app/components/GridDetailDialog/GridDetailDialog').then((mod) => ({
    default: mod.GridDetailDialog,
  }))
);

/**
 * Inner component that renders just the EntityTable + GridDetailDialog.
 * Consumes TableStateProvider from parent context.
 */
export const GridsViewInner = (): React.JSX.Element => {
  const [selectedGridId, setSelectedGridId] = useQueryState('gridDetail', parseAsInteger);

  const openGridDetail = useCallback(
    (gridId: number) => {
      setSelectedGridId(gridId);
    },
    [setSelectedGridId]
  );

  const contextValue = useMemo(() => ({ openGridDetail }), [openGridDetail]);

  return (
    <GridDetailDialogContext.Provider value={contextValue}>
      <EntityTable entityApi={API.GRIDS} entityApiResponseField="grid" columnDefs={GRID_COLUMN_DEFS} />

      {selectedGridId !== null && (
        <Suspense fallback={<CircularProgress />}>
          <GridDetailDialog open onClose={() => setSelectedGridId(null)} gridId={selectedGridId} />
        </Suspense>
      )}
    </GridDetailDialogContext.Provider>
  );
};
