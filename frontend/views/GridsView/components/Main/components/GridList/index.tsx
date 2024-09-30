import React from "react";
import { Props } from "@/views/GridsView/components/Main/components/GridList/types";
import { TableHead } from "@/components/Table/components/TableHead";
import { TableBody } from "@/components/Table/components/TableBody";
import { Table as SDSTable } from "@czi-sds/components";
import { useConnect } from "@/views/GridsView/components/Main/components/GridList/connect";
import { TEST_ID_GRIDS } from "@/views/GridsView/components/Main/components/GridList/constants";

export const GridList = ({ gridList }: Props): JSX.Element => {
  const { table } = useConnect(gridList);
  return (
    <SDSTable data-testid={TEST_ID_GRIDS}>
      <TableHead table={table} />
      <TableBody table={table} />
    </SDSTable>
  );
};
