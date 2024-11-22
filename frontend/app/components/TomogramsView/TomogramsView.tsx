"use client";

import React from "react";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TomogramTable } from "@app/components/TomogramsView/components/TomogramTable/TomogramTable";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { Sidebar } from "@app/common/components/Sidebar/Sidebar";
import { TomogramFilters } from "@app/components/TomogramsView/components/TomogramFilters/TomogramFilters";
import { TOMOGRAM_COLUMN_IDS } from "./components/TomogramTable/columns";
import { SortingState } from "@tanstack/react-table";


export const TomogramsView = (): React.JSX.Element => {
  const initialSortState: SortingState = [{ desc: true, id: TOMOGRAM_COLUMN_IDS.CREATED_AT }];

  return (
    <TableStateProvider
      initialSortState={initialSortState}
    >
      <FilterableTableMain>
      <Sidebar>
          <TomogramFilters />
      </Sidebar>
        <TableWrapper>
          <TomogramTable />
        </TableWrapper>
      </FilterableTableMain >
    </TableStateProvider>
  );
};
