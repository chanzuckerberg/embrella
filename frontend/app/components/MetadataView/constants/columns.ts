import { ColumnDef } from '@tanstack/react-table';
import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { ComputedMetric } from '@app/common/types/metadataViz/metadataSummary';
import { humanize } from '@app/common/utils/string';

export const METADATA_COLUMN_IDS = {
  NAME: 'name',
  MEAN: 'mean',
  MEDIAN: 'median',
  STD: 'std',
} as const;

export const METADATA_COLUMN_DEFS: ColumnDef<ComputedMetric, AccessorReturnType>[] = [
  {
    id: METADATA_COLUMN_IDS.NAME,
    header: humanize(METADATA_COLUMN_IDS.NAME),
    accessorKey: METADATA_COLUMN_IDS.NAME,
    enableSorting: true,
  },
  {
    id: METADATA_COLUMN_IDS.MEAN,
    header: humanize(METADATA_COLUMN_IDS.MEAN),
    accessorKey: METADATA_COLUMN_IDS.MEAN,
    cell: ({ getValue }) => {
      const value = getValue<number>();
      return value != null ? value.toFixed(2) : '-';
    },
    enableSorting: true,
  },
  {
    id: METADATA_COLUMN_IDS.MEDIAN,
    header: humanize(METADATA_COLUMN_IDS.MEDIAN),
    accessorKey: METADATA_COLUMN_IDS.MEDIAN,
    cell: ({ getValue }) => {
      const value = getValue<number>();
      return value != null ? value.toFixed(2) : '-';
    },
    enableSorting: true,
  },
  {
    id: METADATA_COLUMN_IDS.STD,
    header: humanize(METADATA_COLUMN_IDS.STD),
    accessorKey: METADATA_COLUMN_IDS.STD,
    cell: ({ getValue }) => {
      const value = getValue<number>();
      return value != null ? value.toFixed(2) : '-';
    },
    enableSorting: true,
  },
];
