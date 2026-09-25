import { ColumnDef } from '@tanstack/react-table';

import { EntityDataTypes } from '@app/common/types/tableState';
import { formatDate, humanize } from '@app/common/utils/format';
import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import {
  getLinkPropsFromLinkField,
  getLinkCellFromCellContext,
  getLinkPropsFromLinkFieldList,
  getLinkCellListFromCellContext,
} from '@app/common/components/EntityTable/utils/linkUtils';
import { LinkCellProps } from '@app/common/components/EntityTable/types';
import { GridData } from '../types';
import { LabelChip } from '../components/LabelEditor/LabelChip';
import { GridNameCell } from '../components/GridNameCell';
import { GridDetailIconCell } from '../components/GridDetailIconCell';

export const GRID_COLUMN_IDS = {
  CRYOGRID: 'cryogrid',
  SPECIMEN: 'specimen',
  LABELS: 'labels',
  FREEZING_SESSION: 'freezingSession',
  MSI_SESSION: 'msiSession',
  PROJECT: 'project',
  MODIFIED_ON: 'modifiedOn',
};

export const GRID_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: GRID_COLUMN_IDS.CRYOGRID,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as GridData).grid.name,
    cell: ({ row }) => {
      const data = row.original as GridData;
      return <GridNameCell gridId={data.grid.id} name={data.grid.name} trashed={data.grid.trashed} />;
    },
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.CRYOGRID),
    size: 160,
  },
  {
    id: GRID_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps => getLinkPropsFromLinkField((rowData as GridData).project),
    cell: getLinkCellFromCellContext,
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.PROJECT),
    size: 140,
  },
  {
    id: GRID_COLUMN_IDS.SPECIMEN,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps[] =>
      getLinkPropsFromLinkFieldList((rowData as GridData).specimen.samples),
    cell: getLinkCellListFromCellContext,
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.SPECIMEN),
    size: 140,
  },
  {
    id: GRID_COLUMN_IDS.LABELS,
    accessorFn: (rowData: EntityDataTypes): string => {
      const { labels } = rowData as GridData;
      return labels?.map((l) => l.name).join(', ') ?? '';
    },
    cell: ({ row }) => {
      const data = row.original as GridData;
      return <LabelChip gridId={data.grid.id} labels={data.labels ?? []} />;
    },
    enableSorting: false,
    header: 'Labels',
    size: 140,
  },
  {
    id: GRID_COLUMN_IDS.MSI_SESSION,
    accessorFn: (rowData: EntityDataTypes): string =>
      ((rowData as GridData).msiSession ?? []).map((session) => session.name).join(', '),
    cell: ({ row }) => {
      const sessions = (row.original as GridData).msiSession ?? [];
      return (
        <div style={{ maxHeight: '5.6em', overflowY: 'auto', width: '100%' }}>
          {sessions.map((session) => (
            <div key={session.id}>{session.name}</div>
          ))}
        </div>
      );
    },
    enableSorting: false,
    header: 'MSI',
    size: 100,
  },
  {
    id: GRID_COLUMN_IDS.FREEZING_SESSION,
    accessorFn: (rowData: EntityDataTypes): string => {
      const { freezingSession } = rowData as GridData;
      return !freezingSession?.createdAt ? 'No freezing session' : formatDate(freezingSession.createdAt);
    },
    enableSorting: false,
    header: humanize(GRID_COLUMN_IDS.FREEZING_SESSION),
    size: 140,
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
    size: 120,
  },
  {
    id: 'details',
    accessorFn: () => '',
    cell: ({ row }) => {
      const data = row.original as GridData;
      return <GridDetailIconCell gridId={data.grid.id} />;
    },
    enableSorting: false,
    header: '',
    size: 50,
  },
];
