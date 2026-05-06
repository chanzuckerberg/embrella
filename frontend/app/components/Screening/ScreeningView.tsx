'use client';

import React, { Suspense, useCallback, useMemo } from 'react';
import { CircularProgress } from '@mui/material';
import { parseAsInteger, useQueryState } from 'nuqs';

import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { API } from '@app/common/constants/api';
import { GridDetailDialogContext } from '@app/components/GridsView/context/GridDetailDialogContext';

import { SCREENING_COLUMN_DEFS, SCREENING_COLUMN_IDS } from './constants/columns';
import { ScreeningLabelsProvider } from './context/ScreeningLabelsContext';

const GridDetailDialog = React.lazy(() =>
  import('@app/components/GridDetailDialog/GridDetailDialog').then((mod) => ({
    default: mod.GridDetailDialog,
  }))
);

const ScreeningViewInner = (): React.JSX.Element => {
  const [selectedGridId, setSelectedGridId] = useQueryState('gridDetail', parseAsInteger);

  const openGridDetail = useCallback((gridId: number) => setSelectedGridId(gridId), [setSelectedGridId]);
  const contextValue = useMemo(() => ({ openGridDetail }), [openGridDetail]);

  return (
    <GridDetailDialogContext.Provider value={contextValue}>
      <EntityTable entityApi={API.SCREENING_GRIDS} entityApiResponseField="grid" columnDefs={SCREENING_COLUMN_DEFS} />

      {selectedGridId !== null && (
        <Suspense fallback={<CircularProgress />}>
          <GridDetailDialog open onClose={() => setSelectedGridId(null)} gridId={selectedGridId} />
        </Suspense>
      )}
    </GridDetailDialogContext.Provider>
  );
};

export const ScreeningView = (): React.JSX.Element => {
  return (
    <TableStateProvider filterCategories={[]} initialSortState={[{ desc: false, id: SCREENING_COLUMN_IDS.PRIORITY }]}>
      <ScreeningLabelsProvider>
        <TableWrapper>
          <ScreeningViewInner />
        </TableWrapper>
      </ScreeningLabelsProvider>
    </TableStateProvider>
  );
};
