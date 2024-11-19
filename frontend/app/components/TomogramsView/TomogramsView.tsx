"use client";

import React from "react";
import { TableWrapper } from "@/app/common/components/TableWrapper/TableWrapper";
import { FilterableTableMain } from "@/app/common/components/FilterableTableMain/FilterableTableMain";
import { useConnect } from "@app/components/TomogramsView/connect";
import { TomogramTable } from "./TomogramTable/TomogramTable";
import { StyledSidebar } from "../Sidebar/style";


export const TomogramsView = (): React.JSX.Element => {
  const { tomogramList } = useConnect();
  return (
    <FilterableTableMain>
      <StyledSidebar></StyledSidebar>
      <TableWrapper>
        <TomogramTable tomogramList={tomogramList} />
      </TableWrapper>
    </FilterableTableMain>
  );
};
