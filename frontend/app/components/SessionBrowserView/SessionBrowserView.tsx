'use client';

import React, { Suspense, useCallback, useMemo } from 'react';
import { Box, CircularProgress } from '@mui/material';
import { parseAsInteger, useQueryState } from 'nuqs';

import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { EntityTableFilters } from '@app/common/components/EntityTableFilters/EntityTableFilters';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { Sidebar } from '@app/common/components/Sidebar/Sidebar';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { API } from '@app/common/constants/api';
import { GridDetailDialogContext } from '@app/components/GridsView/context/GridDetailDialogContext';

import { SessionSearchBar } from './components/SessionSearchBar';
import { SessionSoftwareSubRow } from './components/SessionSoftwareSubRow';
import { SESSION_COLUMN_DEFS } from './constants/columns';
import { SESSION_FILTER_CATEGORIES, SESSION_FILTER_CONFIGS } from './constants/filters';
import { SessionFilterCategory, SessionFilterId, SessionOverviewData } from './types';

const GridDetailDialog = React.lazy(() =>
  import('@app/components/GridDetailDialog/GridDetailDialog').then((mod) => ({
    default: mod.GridDetailDialog,
  }))
);

const SessionBrowserLayout = (): React.JSX.Element => {
  const [selectedGridId, setSelectedGridId] = useQueryState('gridDetail', parseAsInteger);

  const openGridDetail = useCallback((gridId: number) => setSelectedGridId(gridId), [setSelectedGridId]);
  const contextValue = useMemo(() => ({ openGridDetail }), [openGridDetail]);

  return (
    <GridDetailDialogContext.Provider value={contextValue}>
      <Box>
        <Box sx={{ px: 3, pt: 3, pb: 1 }}>
          <SessionSearchBar />
        </Box>

        <FilterableTableMain>
          <Sidebar>
            <EntityTableFilters<SessionFilterId, SessionFilterCategory>
              entityFilterConfigs={SESSION_FILTER_CONFIGS}
              entityFilterListApi={API.SESSION_OVERVIEW_FILTERLIST}
            />
          </Sidebar>
          <TableWrapper>
            <EntityTable
              entityApi={API.SESSION_OVERVIEW}
              entityApiResponseField="session"
              columnDefs={SESSION_COLUMN_DEFS}
              getSubRows={(row: SessionOverviewData) => row.runs as unknown[]}
              renderSubRow={(row) => <SessionSoftwareSubRow data={row.original as SessionOverviewData} />}
            />
          </TableWrapper>
        </FilterableTableMain>
      </Box>

      {selectedGridId !== null && (
        <Suspense fallback={<CircularProgress />}>
          <GridDetailDialog open onClose={() => setSelectedGridId(null)} gridId={selectedGridId} />
        </Suspense>
      )}
    </GridDetailDialogContext.Provider>
  );
};

export const SessionBrowserView = (): React.JSX.Element => {
  return (
    <TableStateProvider
      filterCategories={SESSION_FILTER_CATEGORIES}
      // Matches the backend's own default, so the first render agrees with
      // what the server actually sorted by.
      initialSortState={[{ desc: true, id: 'sessionDate' }]}
    >
      <SessionBrowserLayout />
    </TableStateProvider>
  );
};
