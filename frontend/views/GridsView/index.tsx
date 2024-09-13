"use client";
import React from "react";
import { GridList } from "@/views/GridsView/components/GridList";
import { GridFilter } from "@/views/GridsView/components/GridFilter";
import { ViewLayout } from "@/views/GridsView/style";
import { Sidebar } from "@/components/Sidebar";
import { useGridList } from "@/views/GridsView/hooks/useGridList/useGridList";
import { Content } from "@/components/Content/style";

export const GridsView = (): JSX.Element => {
  const { gridList, filtersList, onFilter } = useGridList();
  return (
    <ViewLayout>
      <Sidebar>
        <GridFilter filtersList={filtersList} onFilter={onFilter} />
      </Sidebar>
      <Content>
        <GridList gridList={gridList} />
      </Content>
    </ViewLayout>
  );
};
