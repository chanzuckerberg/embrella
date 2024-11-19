import React, { Fragment } from "react";

import { Table as SDSTable } from "@czi-sds/components";

import { TableHead } from "@app/components/Table/components/TableHead";
import { TableBody } from "@app/components/Table/components/TableBody";

import { useConnect } from "@app/components/TomogramsView/components/TomogramTable/connect";

const TEST_ID_DATA_TABLE = "data-table";
// const TEST_ID_GRIDS_PAGINATION = "tomogram-pagination";

export const TomogramTable = (): React.JSX.Element => {
  const { table } = useConnect();
  return (
    <Fragment>
      <SDSTable data-testid={TEST_ID_DATA_TABLE}>
        <TableHead table={table} />
        <TableBody table={table} />
      </SDSTable>
      {/* <Pagination dataTestId={TEST_ID_GRIDS_PAGINATION} table={table} /> */}
    </Fragment>
  );
}
