"use client";

import React from "react";
import { TableWrapper } from "@app/common/components/TableWrapper/TableWrapper";
import { FilterableTableMain } from "@app/common/components/FilterableTableMain/FilterableTableMain";
import { useConnect } from "@app/components/TomogramsView/connect";
import { TomogramTable } from "./TomogramTable/TomogramTable";
import { TableStateProvider } from "@app/common/components/TableStateProvider/TableStateProvider";
import { Sidebar } from "@app/common/components/Sidebar/Sidebar";
import { Filters } from "../Filter/components/Filters";
import { TEST_IDS } from "@app/common/constants/testIds";


export const TomogramsView = (): React.JSX.Element => {
  const { tomogramList, filters, onFilter } = useConnect();
  return (
    <TableStateProvider>
      <FilterableTableMain>
      <Sidebar>
          {/* <GridFilter filtersList={filtersList} /> */}
          <Filters
            dataTestId={TEST_IDS.SIDEBAR_FILTERS}
            filters={filters}
            onFilter={onFilter}
          />
      </Sidebar>
        <TableWrapper>
          <TomogramTable tomogramList={tomogramList} />
        </TableWrapper>
      </FilterableTableMain >
    </TableStateProvider>
  );
};
