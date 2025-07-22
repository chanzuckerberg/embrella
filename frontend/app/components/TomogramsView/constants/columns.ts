import { ColumnDef } from '@tanstack/react-table';

import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { humanize } from '@app/common/utils/string';
import { EntityDataTypes } from '@app/common/types/tableState';
import {
  getLinkPropsFromLinkField,
  getLinkCellFromCellContext,
} from '@app/common/components/EntityTable/utils/linkUtils';
import { LinkCellProps } from '@app/common/components/EntityTable/types';
import { TomogramData } from '../types';
import { ParametersCell } from '../ParametersCell';

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
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).tomograms),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.TOMOGRAMS),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROC_PLAN,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).procPlan),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.PROC_PLAN),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.MSI_SESSION,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).msiSession),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: 'MSI Session',
  },

  {
    id: TOMOGRAM_COLUMN_IDS.METADATA,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => {
      const tomogramData = rowData as TomogramData;

      // Only show metadata link for czii-live processing plans
      const procPlanName = tomogramData.procPlan?.name || '';
      if (!procPlanName.includes('czii-live')) {
        return {
          children: '',
          href: '',
        };
      }

      const sessionName = tomogramData.msiSession?.name || '';
      let runNumber = tomogramData.tomograms?.name || '';
      // Clean the run number by removing (id=XX) and trimming whitespace
      runNumber = runNumber.replace(/\s*\(id=\d+\)/g, '').trim();
      return {
        children: 'View Metadata',
        href: `metadata/view/${encodeURIComponent(sessionName)}/${encodeURIComponent(runNumber)}`,
      };
    },
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.METADATA),
  },
  {
    id: 'metadataParameters',
    accessorFn: (rowData: EntityDataTypes) => rowData,
    cell: ParametersCell,
    enableSorting: false,
    header: 'Parameters',
  },
  {
    id: TOMOGRAM_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps =>
      getLinkPropsFromLinkField((rowData as TomogramData).project),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(TOMOGRAM_COLUMN_IDS.PROJECT),
  },
  {
    id: TOMOGRAM_COLUMN_IDS.GRID,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as TomogramData).grid),
    cell: getLinkCellFromCellContext,
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
