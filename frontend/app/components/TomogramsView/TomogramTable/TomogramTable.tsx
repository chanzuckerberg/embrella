import React, { Fragment } from "react";

import { Table as SDSTable } from "@czi-sds/components";

import { TableHead } from "@app/components/Table/components/TableHead";
import { TableBody } from "@app/components/Table/components/TableBody";

import { TomogramData } from "@app/common/types/tomogram";
import { EntityList } from "@app/common/types/types";
import { useConnect } from "@app/components/TomogramsView/TomogramTable/connect";

interface Props {
  tomogramList?: EntityList<TomogramData, "tomograms">;
}

const TEST_ID_GRIDS = "tomograms";
// const TEST_ID_GRIDS_PAGINATION = "tomogram-pagination";

export const TomogramTable = ({ tomogramList }: Props): React.JSX.Element => {
  const { table } = useConnect(tomogramList);
  return (
    <Fragment>
      <SDSTable data-testid={TEST_ID_GRIDS}>
        <TableHead table={table} />
        <TableBody table={table} />
      </SDSTable>
      {/* <Pagination dataTestId={TEST_ID_GRIDS_PAGINATION} table={table} /> */}
    </Fragment>
  );
}
