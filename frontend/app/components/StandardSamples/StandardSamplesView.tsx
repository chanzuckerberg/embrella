'use client';

import React, { Suspense, useCallback, useMemo } from 'react';
import { parseAsInteger, useQueryState } from 'nuqs';
import { CircularProgress } from '@mui/material';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { API } from '@app/common/constants/api';
import { GridDetailDialogContext } from '@app/components/GridsView/context/GridDetailDialogContext';
import { STANDARD_SAMPLE_COLUMN_DEFS } from './constants/columns';
import { StandardSampleData } from './types';
import { StandardSampleSubRow } from './components/StandardSampleSubRow';

const GridDetailDialog = React.lazy(() =>
  import('@app/components/GridDetailDialog/GridDetailDialog').then((mod) => ({
    default: mod.GridDetailDialog,
  }))
);

const StandardSamplesViewInner = (): React.JSX.Element => {
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
        entityApi={API.STANDARD_SAMPLES}
        entityApiResponseField="specimen"
        columnDefs={STANDARD_SAMPLE_COLUMN_DEFS}
        getSubRows={(row: StandardSampleData) => row.grids as unknown[]}
        renderSubRow={(row) => <StandardSampleSubRow grids={(row.original as StandardSampleData).grids} />}
      />

      {selectedGridId !== null && (
        <Suspense fallback={<CircularProgress />}>
          <GridDetailDialog open onClose={() => setSelectedGridId(null)} gridId={selectedGridId} />
        </Suspense>
      )}
    </GridDetailDialogContext.Provider>
  );
};

export const StandardSamplesView = (): React.JSX.Element => {
  return (
    <TableStateProvider filterCategories={[]} initialSortState={[{ desc: true, id: 'availableGridCount' }]}>
      <TableWrapper>
        <StandardSamplesViewInner />
      </TableWrapper>
    </TableStateProvider>
  );
};
