import React from "react";
import { Content } from "@app/components/Content/style";
import { FilterableTableMain } from "@/app/common/components/FilterableTableMain/FilterableTableMain";
import { Sidebar } from "@app/components/Sidebar";
import { useConnect } from "@/views/GridsView/components/Main/connect";
import { GridFilter } from "@/views/GridsView/components/Main/components/GridFilter";
import { GridList } from "@/views/GridsView/components/Main/components/GridList";

export const Main = (): JSX.Element => {
  const { gridList, filtersList } = useConnect();
  return (
    <FilterableTableMain>
      <Sidebar>
        <GridFilter filtersList={filtersList} />
      </Sidebar>
      <Content>
        <GridList gridList={gridList} />
      </Content>
    </FilterableTableMain>
  );
};
