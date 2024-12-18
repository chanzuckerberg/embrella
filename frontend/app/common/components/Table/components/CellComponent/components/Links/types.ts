import { CellContext, RowData } from "@tanstack/react-table";
import { LinkTValue } from "@/app/common/components/Table/components/CellComponent/types";

export type Props<TData extends RowData> = CellContext<TData, LinkTValue[]>;
