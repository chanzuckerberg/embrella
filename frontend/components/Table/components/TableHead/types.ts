import { RowData, Table } from "@tanstack/react-table";

export interface Props<TData extends RowData> {
  table: Table<TData>;
}
