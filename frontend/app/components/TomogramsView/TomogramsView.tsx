'use client';

import React from 'react';
import { TableWrapper } from '@app/common/components/TableWrapper/TableWrapper';
import { FilterableTableMain } from '@app/common/components/FilterableTableMain/FilterableTableMain';
import { TableStateProvider } from '@app/common/components/TableStateProvider/TableStateProvider';
import { Sidebar } from '@app/common/components/Sidebar/Sidebar';
import { TOMOGRAM_COLUMN_DEFS, TOMOGRAM_COLUMN_IDS } from './constants/columns';
import { EntityTable } from '@app/common/components/EntityTable/EntityTable';
import { API } from '@app/common/constants/api';
import { TomogramFilterId, TomogramFilterCategory } from './types';
import { TOMOGRAM_FILTER_CONFIGS } from './constants/filters';
import { EntityTableFilters } from '@app/common/components/EntityTableFilters/EntityTableFilters';

export const TomogramsView = (): React.JSX.Element => {
  return (
    <TableStateProvider
      filterCategories={['project', 'sample', 'user', 'date', 'screeningSession', 'msiSession', 'procPlan']}
      initialSortState={[{ desc: true, id: TOMOGRAM_COLUMN_IDS.UPDATED_AT }]}
    >
      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters<TomogramFilterId, TomogramFilterCategory>
            entityFilterConfigs={TOMOGRAM_FILTER_CONFIGS}
            entityFilterListApi={API.TOMOGRAMS_FILTERLIST}
          />
        </Sidebar>
        <TableWrapper>
          <EntityTable entityApi={API.TOMOGRAMS} entityApiResponseField="tomograms" columnDefs={TOMOGRAM_COLUMN_DEFS} />
        </TableWrapper>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
