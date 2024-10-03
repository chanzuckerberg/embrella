import React, { Fragment } from "react";
import { Props } from "@/views/GridsView/components/Main/components/GridList/types";
import { TableHead } from "@/components/Table/components/TableHead";
import { TableBody } from "@/components/Table/components/TableBody";
import { Table as SDSTable } from "@czi-sds/components";
import { useConnect } from "@/views/GridsView/components/Main/components/GridList/connect";
import { TEST_ID_GRIDS } from "@/views/GridsView/components/Main/components/GridList/constants";
import { Pagination } from "@/components/Table/components/Pagination";

export const GridList = ({ gridList }: Props): JSX.Element => {
  const { table } = useConnect(gridList);
  return (
    <Fragment>
      <SDSTable data-testid={TEST_ID_GRIDS}>
        <TableHead table={table} />
        <TableBody table={table} />
      </SDSTable>
      <Pagination table={table} />
    </Fragment>
  );
};
