import { Fragment } from "react";
import { Table as SDSTable } from "@czi-sds/components";

import { TableHead } from "@app/components/Table/components/TableHead";
import { TableBody } from "@app/components/Table/components/TableBody";

import { Pagination } from "@app/components/Table/components/Pagination";
import { EntityDataTypes, EntityList } from "@app/common/types/tableState";
import { ColumnDef } from "@tanstack/react-table";
import { AccessorReturnType } from "../TomogramsView/components/TomogramTable/columns";
import { useConnect } from "./connect";
import { ApiPrimaryEntityAttribute } from "./types";

const TEST_ID_ENTITY_TABLE = "entity-table";
const TEST_ID_ENTITY_TABLE_PAGINATION = "entity-table-pagination";

interface EntityTableProps {
  entityList: EntityList,
  entityApiResponseField: ApiPrimaryEntityAttribute,
  columnDefs: ColumnDef<EntityDataTypes, AccessorReturnType>[],
};

export const EntityTable = ({ entityList, entityApiResponseField, columnDefs }: EntityTableProps): React.JSX.Element => {
  const { table } = useConnect(entityList, entityApiResponseField, columnDefs);
  return (
    <Fragment>
      <SDSTable data-testid={TEST_ID_ENTITY_TABLE}>
        <TableHead table={table} />
        <TableBody table={table} />
      </SDSTable>
      <Pagination dataTestId={TEST_ID_ENTITY_TABLE_PAGINATION} table={table} />
    </Fragment>
  );
};
