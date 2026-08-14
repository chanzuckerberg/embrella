import { ColumnDef } from '@tanstack/react-table';

import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { humanize } from '@app/common/utils/format';
import { EntityDataTypes } from '@app/common/types/tableState';
import { TomogramData } from '../types';
import { ParametersCell } from '../ParametersCell';
import { MetadataCell } from '../MetadataCell';

export const TOMOGRAM_COLUMN_IDS = {
  TOMOGRAMS: 'tomograms',
  PROC_PLAN: 'procPlan',
  MSI_SESSION: 'msiSession',
  METADATA: 'metadata',
  PROJECT: 'project',
  GRID: 'grid',
  NOTES: 'notes',
  UPDATED_AT: 'updatedAt',
};

export const TOMOGRAM_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: TOMOGRAM_COLUMN_IDS.TOMOGRAMS,
    accessorKey: 'tomograms.name',
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.TOMOGRAMS),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROC_PLAN,
    accessorKey: 'procPlan.name',
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.PROC_PLAN),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.MSI_SESSION,
    accessorKey: 'msiSession.name',
    enableSorting: false,
    header: 'MSI Session',
  },

  {
    id: TOMOGRAM_COLUMN_IDS.METADATA,
    cell: MetadataCell,
    enableSorting: false,
    header: 'Session Summary',
  },
  {
    id: 'metadataParameters',
    cell: ParametersCell,
    enableSorting: false,
    header: 'Parameters',
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROJECT,
    accessorKey: 'project.name',
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.PROJECT),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.GRID,
    accessorKey: 'grid.name',
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.GRID),
  },
  // {
  //   id: TOMOGRAM_COLUMN_IDS.NOTES,
  //   accessorFn: (rowData: EntityDataTypes): string => (rowData as TomogramData).procRun.notes,
  //   enableSorting: false,
  //   header: humanize(TOMOGRAM_COLUMN_IDS.NOTES),
  // },
  {
    id: TOMOGRAM_COLUMN_IDS.UPDATED_AT,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as TomogramData).procRun.updatedAt,
    enableSorting: true,
    header: humanize(TOMOGRAM_COLUMN_IDS.UPDATED_AT),
  },
];
