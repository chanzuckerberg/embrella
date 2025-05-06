import { ColumnDef } from '@tanstack/react-table';

import { EntityDataTypes } from '@app/common/types/tableState';
import { humanize } from '@app/common/utils/string';
import { formatDate } from '@app/common/utils/date';
import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import {
  getLinkPropsFromLinkField,
  getLinkCellFromCellContext,
  getLinkPropsFromLinkFieldList,
  getLinkCellListFromCellContext,
} from '@app/common/components/EntityTable/utils/linkUtils';
import { LinkCellProps } from '@app/common/components/EntityTable/types';
import { GridData } from '../types';

export const GRID_COLUMN_IDS = {
  CRYOGRID: 'cryogrid',
  SPECIMEN: 'specimen',
  FREEZING_SESSION: 'freezingSession',
  MSI_SESSION: 'msiSession',
  PROJECT: 'project',
  MODIFIED_ON: 'modifiedOn',
};

export const GRID_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: GRID_COLUMN_IDS.CRYOGRID,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as GridData).grid),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.CRYOGRID),
  },
  {
    id: GRID_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as GridData).project),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.PROJECT),
  },
  {
    id: GRID_COLUMN_IDS.SPECIMEN,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps[] =>
      getLinkPropsFromLinkFieldList((rowData as GridData).specimen.samples),
    cell: getLinkCellListFromCellContext,
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.SPECIMEN),
  },
  {
    id: GRID_COLUMN_IDS.MSI_SESSION,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps[] =>
      getLinkPropsFromLinkFieldList((rowData as GridData).msiSession),
    cell: getLinkCellListFromCellContext,
    enableSorting: false,
    header: 'MSI',
  },
  {
    id: GRID_COLUMN_IDS.FREEZING_SESSION,
    accessorFn: (rowData: EntityDataTypes): string => formatDate((rowData as GridData).freezingSession.createdAt),
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.FREEZING_SESSION),
  },
  {
    id: GRID_COLUMN_IDS.MODIFIED_ON,
    accessorFn: (rowData: EntityDataTypes): string => {
      const {
        grid: { updatedAt },
      } = rowData as GridData;
      return !updatedAt ? '-' : formatDate(updatedAt);
    },
    enableSorting: true,
    header: 'Updated At',
  },
];
