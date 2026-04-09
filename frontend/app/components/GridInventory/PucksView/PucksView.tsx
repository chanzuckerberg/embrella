'use client';

import React, { Suspense, useCallback, useMemo } from 'react';
import { parseAsInteger, useQueryState } from 'nuqs';
import { CircularProgress } from '@mui/material';
import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { API } from '@app/common/constants/api';
import { GridDetailDialogContext } from '@app/components/GridsView/context/GridDetailDialogContext';
import { PUCK_COLUMN_DEFS } from './constants/columns';
import { PuckData } from './types';
import { PuckSubRow } from './components/PuckSubRow';

const GridDetailDialog = React.lazy(() =>
  import('@app/components/GridDetailDialog/GridDetailDialog').then((mod) => ({
    default: mod.GridDetailDialog,
  }))
);

/**
 * Inner component that renders just the EntityTable + GridDetailDialog.
 * Consumes TableStateProvider from parent context.
 */
export const PucksViewInner = (): React.JSX.Element => {
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
      <EntityTable
        entityApi={API.PUCKS_VIEW}
        entityApiResponseField="puck"
        columnDefs={PUCK_COLUMN_DEFS}
        getSubRows={(row: PuckData) => row.gridBoxes as unknown[]}
        renderSubRow={(row) => <PuckSubRow gridBoxes={(row.original as PuckData).gridBoxes} />}
      />

      {selectedGridId !== null && (
        <Suspense fallback={<CircularProgress />}>
          <GridDetailDialog open onClose={() => setSelectedGridId(null)} gridId={selectedGridId} />
        </Suspense>
      )}
    </GridDetailDialogContext.Provider>
  );
};
