'use client';

import React, { useMemo, useContext } from 'react';
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
import { PucksViewInner } from './PucksView/PucksView';
import { SHARED_FILTER_CONFIGS, GridFilterId, GridFilterCategory } from './constants/filters';
import { API } from '@app/common/constants/api';
import { getFilterSearchParamValues } from '@app/common/utils/searchParam';
import { useFetchData } from '@hooks/useFetchData/useFetchData';
import { SEARCH_PARAM_NAME } from '@app/common/types/search';

const TABS = ['grids', 'gridBoxes', 'pucks'] as const;
type TabValue = (typeof TABS)[number];

const TAB_CONFIG: Record<
  TabValue,
  {
    label: string;
    countKey: keyof GridInventoryCounts;
    placeholder: string;
    filtersListApi: API;
    searchSuggestionsApi: API;
    component: React.ComponentType;
  }
> = {
  grids: {
    label: 'Grids',
    countKey: 'grids',
    placeholder: 'Search grids...',
    filtersListApi: API.GRIDS_FILTERS_LIST,
    searchSuggestionsApi: API.GRIDS_SEARCH_SUGGESTIONS,
    component: GridsViewInner,
  },
  gridBoxes: {
    label: 'Grid Boxes',
    countKey: 'gridBoxes',
    placeholder: 'Search grid boxes...',
    filtersListApi: API.GRID_BOXES_FILTERS_LIST,
    searchSuggestionsApi: API.GRID_BOXES_SEARCH_SUGGESTIONS,
    component: GridBoxesViewInner,
  },
  pucks: {
    label: 'Pucks',
    countKey: 'pucks',
    placeholder: 'Search pucks...',
    filtersListApi: API.PUCKS_VIEW_FILTERS_LIST,
    searchSuggestionsApi: API.PUCKS_VIEW_SEARCH_SUGGESTIONS,
    component: PucksViewInner,
  },
};

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

interface GridInventoryCounts {
  grids: number;
  gridBoxes: number;
  pucks: number;
}

function useTabCounts(): GridInventoryCounts | undefined {
  const state = useContext(TableStateContext);

  const searchParam = useMemo(
    () => ({
      [SEARCH_PARAM_NAME.QUERY]: getFilterSearchParamValues(state),
    }),
    [state]
  );

  const { data } = useFetchData<GridInventoryCounts>(API.GRID_INVENTORY_COUNTS, searchParam);

  return data;
}

function GridInventoryInner(): React.JSX.Element {
  const [activeTab, setActiveTab] = useQueryState('tab', parseAsString.withDefault('grids'));
  const tabIndex = Math.max(TABS.indexOf(activeTab as TabValue), 0);
  const counts = useTabCounts();
  const config = TAB_CONFIG[TABS[tabIndex]];
  const ActiveComponent = config.component;

  const handleTabChange = (_: React.SyntheticEvent, newIndex: number) => {
    setActiveTab(TABS[newIndex]);
  };

  return (
    <Box>
      <SearchBar placeholder={config.placeholder} suggestionsApi={config.searchSuggestionsApi} />

      <Box sx={{ pt: 0.5, mb: -5 }}>
        <Tabs value={tabIndex} onChange={handleTabChange} sdsSize="large">
          {TABS.map((tab) => {
            const tabConfig = TAB_CONFIG[tab];
            const count = counts?.[tabConfig.countKey];
            const label = count != null ? `${tabConfig.label} (${count})` : tabConfig.label;
            return <Tab key={tab} label={label} />;
          })}
        </Tabs>
      </Box>

      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters<GridFilterId, GridFilterCategory>
            entityFilterConfigs={SHARED_FILTER_CONFIGS}
            entityFilterListApi={config.filtersListApi}
          />
        </Sidebar>
        <TableWrapper>
          <ActiveComponent />
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
