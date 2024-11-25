"use client";

import React from "react";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { Sidebar } from "@app/common/components/Sidebar/Sidebar";
import { TOMOGRAM_COLUMN_DEFS, TOMOGRAM_COLUMN_IDS } from "./columns";
import { SortingState } from "@tanstack/react-table";
import { EntityTable } from "@app/common/components/EntityTable/EntityTable";
import { API } from "@app/common/constants/api";
import {
  TOMOGRAM_FILTER_CONFIGS,
  TOMOGRAM_FILTER_IDS,
  TomogramFilterCategory,
} from "./types";
import { EntityTableFilters } from "@/app/common/components/EntityTableFilters/EntityTableFilters";

export const TomogramsView = (): React.JSX.Element => {
  const initialSortState: SortingState = [
    { desc: true, id: TOMOGRAM_COLUMN_IDS.CREATED_AT },
  ];

  return (
    <TableStateProvider initialSortState={initialSortState}>
      <FilterableTableMain>
        <Sidebar>
          <EntityTableFilters<TOMOGRAM_FILTER_IDS, TomogramFilterCategory>
            entityFilterConfigs={TOMOGRAM_FILTER_CONFIGS}
            entityFilterListApi={API.TOMOGRAMS_FILTERLIST_V1}
          />
        </Sidebar>
        <TableWrapper>
          <EntityTable
            entityApi={API.TOMOGRAMS_V1}
            entityApiResponseField="tomograms"
            columnDefs={TOMOGRAM_COLUMN_DEFS}
          />
        </TableWrapper>
      </FilterableTableMain>
    </TableStateProvider>
  );
};
