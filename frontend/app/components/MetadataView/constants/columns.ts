import { ColumnDef } from "@tanstack/react-table";
import { AccessorReturnType } from "@app/common/components/EntityTable/types";
import { ComputedMetric } from "@app/common/types/metadataViz/metadataSummary";
import { humanize } from "@app/common/utils/string";
import { EntityDataTypes } from "@app/common/types/tableState";

export const METADATA_COLUMN_IDS = {
  NAME: "name",
  MEAN: "mean",
  MEDIAN: "median",
  STD: "std",
} as const;

export const METADATA_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: METADATA_COLUMN_IDS.NAME,
    header: humanize(METADATA_COLUMN_IDS.NAME),
    accessorKey: "name",
    enableSorting: true,
  },
  {
    id: METADATA_COLUMN_IDS.MEAN,
    header: humanize(METADATA_COLUMN_IDS.MEAN),
    accessorKey: "mean",
    cell: ({ getValue }) => {
      const value = getValue<number>();
      return value != null ? value.toFixed(2) : '-';
    },
    enableSorting: true,
  },
  {
    id: METADATA_COLUMN_IDS.MEDIAN,
    header: humanize(METADATA_COLUMN_IDS.MEDIAN),
    accessorKey: "median",
    cell: ({ getValue }) => {
      const value = getValue<number>();
      return value != null ? value.toFixed(2) : '-';
    },
    enableSorting: true,
  },
  {
    id: METADATA_COLUMN_IDS.STD,
    header: humanize(METADATA_COLUMN_IDS.STD),
    accessorKey: "std",
    cell: ({ getValue }) => {
      const value = getValue<number>();
      return value != null ? value.toFixed(2) : '-';
    },
    enableSorting: true,
  },
];
