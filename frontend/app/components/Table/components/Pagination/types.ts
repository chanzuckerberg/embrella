import { RowData, Table } from "@tanstack/react-table";

export interface Props<TData extends RowData> {
  dataTestId?: string;
  table: Table<TData>;
}
