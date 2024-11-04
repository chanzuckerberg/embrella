import React from "react";
import { ViewLayout } from "@/views/GridsView/style";
import { Sidebar } from "@app/components/Sidebar";
import { useConnect } from "@/views/GridsView/components/Main/connect";
import { Content } from "@app/components/Content/style";
import { GridFilter } from "@/views/GridsView/components/Main/components/GridFilter";
import { GridList } from "@/views/GridsView/components/Main/components/GridList";

export const Main = (): JSX.Element => {
  const { gridList, filtersList } = useConnect();
  return (
    <ViewLayout>
      <Sidebar>
        <GridFilter filtersList={filtersList} />
      </Sidebar>
      <Content>
        <GridList gridList={gridList} />
      </Content>
    </ViewLayout>
  );
};
