import { Checkbox, IconButton } from '@mui/material';
import { ColumnDef } from '@tanstack/react-table';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';

import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { EntityDataTypes } from '@app/common/types/tableState';

import { DirectorySummary, ORIGIN_LABELS, STATUS_LABELS, isActionablePath } from '../types';
import { OriginBadge } from '../components/OriginBadge';
import { DirectoryActionButton } from '../components/DirectoryActionButton';

export const DIRECTORY_COLUMN_IDS = {
  SELECT: 'select',
  EXPAND: 'expand',
  PATH: 'path',
  ORIGIN: 'origin',
  FILE_COUNT: 'file_count',
  TOTAL_SIZE: 'total_size_bytes',
  OWNER: 'owner_username',
  PRESERVE_STATUS: 'preserve_status',
  NEWEST_MTIME: 'newest_file_mtime',
  ACTIONS: 'actions',
};

export const DIRECTORY_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: DIRECTORY_COLUMN_IDS.SELECT,
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllRowsSelected()}
        indeterminate={table.getIsSomeRowsSelected()}
        onChange={table.getToggleAllRowsSelectedHandler()}
        inputProps={{ 'aria-label': 'Select all rows' }}
        size="small"
      />
    ),
    cell: ({ row }) => {
      const rowData = row.original as DirectorySummary;
      const actionable = isActionablePath(rowData.path);
      if (!actionable) {
        return null; // Hide checkbox for non-actionable directories
      }
      return (
        <Checkbox
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          inputProps={{ 'aria-label': 'Select row' }}
          size="small"
        />
      );
    },
    enableSorting: false,
    size: 40,
  },
  {
    id: DIRECTORY_COLUMN_IDS.EXPAND,
    header: '',
    cell: ({ row }) => {
      const isExpanded = row.getIsExpanded?.() ?? false;
      return (
        <IconButton
          size="small"
          onClick={() => row.toggleExpanded?.()}
          aria-label={isExpanded ? 'Collapse row' : 'Expand row'}
        >
          {isExpanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
        </IconButton>
      );
    },
    enableSorting: false,
    size: 40,
  },
  {
    id: DIRECTORY_COLUMN_IDS.PATH,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as DirectorySummary).path,
    enableSorting: true,
    header: 'Path',
    size: 400,
  },
  {
    id: DIRECTORY_COLUMN_IDS.ORIGIN,
    accessorFn: (rowData: EntityDataTypes): string => {
      const origin = (rowData as DirectorySummary).origin;
      return ORIGIN_LABELS[origin] || origin;
    },
    cell: ({ row }) => {
      const rowData = row.original as DirectorySummary;
      return <OriginBadge origin={rowData.origin} />;
    },
    enableSorting: false,
    header: 'Origin',
    size: 130,
  },
  {
    id: DIRECTORY_COLUMN_IDS.FILE_COUNT,
    accessorFn: (rowData: EntityDataTypes): string => {
      const count = (rowData as DirectorySummary).file_count;
      return count != null ? count.toLocaleString() : '0';
    },
    enableSorting: true,
    header: 'Files',
    size: 80,
  },
  {
    id: DIRECTORY_COLUMN_IDS.TOTAL_SIZE,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as DirectorySummary).total_size_display || '0 B',
    enableSorting: true,
    header: 'Size',
    size: 100,
  },
  {
    id: DIRECTORY_COLUMN_IDS.OWNER,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as DirectorySummary).owner_username || 'Unknown',
    enableSorting: false,
    header: 'Owner',
    size: 120,
  },
  {
    id: DIRECTORY_COLUMN_IDS.PRESERVE_STATUS,
    accessorFn: (rowData: EntityDataTypes): string => {
      const status = (rowData as DirectorySummary).preserve_status;
      return STATUS_LABELS[status] || status;
    },
    enableSorting: true,
    header: 'Status',
    size: 100,
  },
  {
    id: DIRECTORY_COLUMN_IDS.NEWEST_MTIME,
    accessorFn: (rowData: EntityDataTypes): string => {
      const mtime = (rowData as DirectorySummary).newest_file_mtime;
      if (!mtime) return 'N/A';
      try {
        return new Date(mtime).toLocaleDateString();
      } catch {
        return mtime;
      }
    },
    enableSorting: true,
    header: 'Last Modified',
    size: 120,
  },
];

/**
 * Creates the action column with a callback for when actions complete.
 */
export const createActionColumn = (onActionComplete: () => void): ColumnDef<EntityDataTypes, AccessorReturnType> => ({
  id: DIRECTORY_COLUMN_IDS.ACTIONS,
  cell: ({ row }) => {
    const rowData = row.original as DirectorySummary;
    const actionable = isActionablePath(rowData.path);
    return (
      <DirectoryActionButton
        directoryId={rowData.id}
        currentStatus={rowData.preserve_status}
        onActionComplete={onActionComplete}
        disabled={!actionable}
      />
    );
  },
  enableSorting: false,
  header: 'Actions',
  size: 80,
});
