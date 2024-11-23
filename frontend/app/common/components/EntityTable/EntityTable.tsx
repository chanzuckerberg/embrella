import { Fragment } from "react";
import { Table as SDSTable } from "@czi-sds/components";

import { TableHead } from "@app/components/Table/components/TableHead";
import { TableBody } from "@app/components/Table/components/TableBody";

import { Pagination } from "@app/components/Table/components/Pagination";
import { EntityDataTypes } from "@app/common/types/tableState";
import { ColumnDef } from "@tanstack/react-table";
import { AccessorReturnType } from "@app/components/TomogramsView/columns";
import { useConnect } from "./connect";
import { ApiPrimaryEntityAttribute } from "./types";
import { API } from "@/app/common/constants/api";
import { TEST_IDS } from "@app/common/constants/testIds";

interface EntityTableProps {
  entityApi: API;
  entityApiResponseField: ApiPrimaryEntityAttribute;
  columnDefs: ColumnDef<EntityDataTypes, AccessorReturnType>[];
}

export const EntityTable = ({
  entityApi,
  entityApiResponseField,
  columnDefs,
}: EntityTableProps): React.JSX.Element => {
  const { table } = useConnect(entityApi, entityApiResponseField, columnDefs);
  return (
    <Fragment>
      <SDSTable data-testid={TEST_IDS.ENTITY_TABLE}>
        <TableHead table={table} />
        <TableBody table={table} />
      </SDSTable>
      <Pagination dataTestId={TEST_IDS.ENTITY_TABLE_PAGINATION} table={table} />
    </Fragment>
  );
};
