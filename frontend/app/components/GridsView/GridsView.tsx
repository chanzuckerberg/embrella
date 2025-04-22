"use client";

import React from "react";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { Sidebar } from "@app/common/components/Sidebar/Sidebar";
import { GRID_COLUMN_DEFS, GRID_COLUMN_IDS } from "./constants/columns";
import { SortingState } from "@tanstack/react-table";
import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { GET_API } from "@app/common/constants/api";
import { GridFilterId, GridFilterCategory } from "./types";
import { GRID_FILTER_CONFIGS } from "./constants/filters";
import { EntityTableFilters } from "@app/common/components/EntityTableFilters/EntityTableFilters";

export const GridsView = (): React.JSX.Element => {
  const initialSortState: SortingState = [
    { desc: true, id: GRID_COLUMN_IDS.MODIFIED_ON },
  ];

  return (
    <TableStateProvider initialSortState={initialSortState}>
      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters<GridFilterId, GridFilterCategory>
            entityFilterConfigs={GRID_FILTER_CONFIGS}
            entityFilterListApi={GET_API.GRIDS_FILTERS_LIST}
          />
        </Sidebar>
        <TableWrapper>
          <EntityTable
            entityApi={GET_API.GRIDS}
            entityApiResponseField="grid"
            columnDefs={GRID_COLUMN_DEFS}
          />
        </TableWrapper>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
