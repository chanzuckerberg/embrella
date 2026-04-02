'use client';

import React, { useContext, useMemo } from 'react';
import { Box } from '@mui/material';
import { Tab, Tabs } from '@czi-sds/components';
import { parseAsString, useQueryState } from 'nuqs';
import { TableStateProvider, TableStateContext } from '@app/common/components/TableStateProvider/TableStateProvider';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { Sidebar } from '@app/common/components/Sidebar/Sidebar';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { EntityTableFilters } from '@app/common/components/EntityTableFilters/EntityTableFilters';
import { SearchBar } from '@app/components/GridsView/components/SearchBar/SearchBar';
import { GridsViewInner } from '@app/components/GridsView/GridsView';
import { GridBoxesViewInner } from './GridBoxesView/GridBoxesView';
import { SHARED_FILTER_CONFIGS, GridFilterId, GridFilterCategory } from './constants/filters';
import { API } from '@app/common/constants/api';
import { getFilterSearchParamValues } from '@app/common/utils/searchParam';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { ApiListResponse, EntityDataTypes } from '@app/common/types/tableState';
import { SEARCH_PARAM_NAME } from '@app/common/types/search';

const TABS = ['grids', 'gridBoxes'] as const;
type TabValue = (typeof TABS)[number];

const FILTER_CATEGORIES = [
  'project',
  'user',
  'sample',
  'label',
  'msiSession',
  'search',
  'cassette',
  'date',
  'puck',
  'screeningSession',
  'status',
];

function useTabCounts() {
  const state = useContext(TableStateContext);

  const searchParam = useMemo(
    () => ({
      [SEARCH_PARAM_NAME.QUERY]: [
        ...getFilterSearchParamValues(state),
        { category: 'page', value: [1] },
        { category: 'pageSize', value: [1] },
      ],
    }),
    [state]
  );

  const { data: gridsData } = useFetchData<ApiListResponse<EntityDataTypes>>(API.GRIDS, searchParam);
  const { data: gridBoxesData } = useFetchData<ApiListResponse<EntityDataTypes>>(API.GRID_BOXES, searchParam);

  return {
    gridsCount: gridsData?.pagination?.totalResults,
    gridBoxesCount: gridBoxesData?.pagination?.totalResults,
  };
}

function GridInventoryInner(): React.JSX.Element {
  const [activeTab, setActiveTab] = useQueryState('tab', parseAsString.withDefault('grids'));
  const tabIndex = Math.max(TABS.indexOf(activeTab as TabValue), 0);
  const { gridsCount, gridBoxesCount } = useTabCounts();

  const handleTabChange = (_: React.SyntheticEvent, newIndex: number) => {
    setActiveTab(TABS[newIndex]);
  };

  const gridsLabel = gridsCount != null ? `Grids (${gridsCount})` : 'Grids';
  const gridBoxesLabel = gridBoxesCount != null ? `Grid Boxes (${gridBoxesCount})` : 'Grid Boxes';

  const isGrids = tabIndex === 0;

  return (
    <Box>
      <SearchBar
        placeholder={isGrids ? 'Search grids...' : 'Search grid boxes...'}
        suggestionsApi={isGrids ? API.GRIDS_SEARCH_SUGGESTIONS : API.GRID_BOXES_SEARCH_SUGGESTIONS}
      />

      <Box sx={{ pt: 0.5, mb: -5 }}>
        <Tabs value={tabIndex} onChange={handleTabChange} sdsSize="large">
          <Tab label={gridsLabel} />
          <Tab label={gridBoxesLabel} />
        </Tabs>
      </Box>

      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters<GridFilterId, GridFilterCategory>
            entityFilterConfigs={SHARED_FILTER_CONFIGS}
            entityFilterListApi={isGrids ? API.GRIDS_FILTERS_LIST : API.GRID_BOXES_FILTERS_LIST}
          />
        </Sidebar>
        <TableWrapper>
          {tabIndex === 0 && <GridsViewInner />}
          {tabIndex === 1 && <GridBoxesViewInner />}
        </TableWrapper>
      </FilterableTableMain>
    </Box>
  );
}

export const GridInventory = (): React.JSX.Element => {
  return (
    <TableStateProvider filterCategories={FILTER_CATEGORIES} initialSortState={[{ desc: true, id: 'id' }]}>
      <GridInventoryInner />
    </TableStateProvider>
  );
};
