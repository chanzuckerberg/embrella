"use client";

import React from "react";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { TomogramTable } from "@app/components/TomogramsView/components/TomogramTable/TomogramTable";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { Sidebar } from "@app/common/components/Sidebar/Sidebar";
import { TomogramFilters } from "@app/components/TomogramsView/components/TomogramFilters/TomogramFilters";


export const TomogramsView = (): React.JSX.Element => {
  return (
    <TableStateProvider>
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
