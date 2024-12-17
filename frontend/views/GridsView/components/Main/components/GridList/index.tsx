import React, { Fragment } from "react";
import { Props } from "@/views/GridsView/components/Main/components/GridList/types";
import { TableHead } from "@/app/common/components/Table/components/TableHead";
import { TableBody } from "@/app/common/components/Table/components/TableBody";
import { Table as SDSTable } from "@czi-sds/components";
import { useConnect } from "@/views/GridsView/components/Main/components/GridList/connect";
import {
  TEST_ID_GRIDS,
  TEST_ID_GRIDS_PAGINATION,
} from "@/views/GridsView/components/Main/components/GridList/constants";
import { Pagination } from "@/app/common/components/Table/components/Pagination";

export const GridList = ({ gridList }: Props): JSX.Element => {
  const { table } = useConnect(gridList);
  return (
    <Fragment>
      <SDSTable data-testid={TEST_ID_GRIDS}>
        <TableHead table={table} />
        <TableBody table={table} />
      </SDSTable>
      <Pagination dataTestId={TEST_ID_GRIDS_PAGINATION} table={table} />
    </Fragment>
  );
};
