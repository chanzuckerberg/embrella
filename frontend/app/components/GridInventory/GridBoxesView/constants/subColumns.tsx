import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { ColumnDef } from '@tanstack/react-table';

import { LabelChip } from '@app/components/GridsView/components/LabelEditor/LabelChip';
import { GridBoxChildGrid } from '../types';

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString();
};

const BoolIcon = ({ value }: { value: boolean }) =>
  value ? <CheckIcon fontSize="small" color="success" /> : <CloseIcon fontSize="small" color="disabled" />;

export const GRID_BOX_SUB_COLUMN_IDS = {
  NAME: 'name',
  PROJECT: 'project',
  SPECIMEN: 'specimen',
  POSITION: 'position',
  CLIPPED: 'clipped',
  TRASHED: 'trashed',
  LABELS: 'labels',
  NOTES: 'notes',
  USER: 'user',
  CREATED: 'created',
};

export const GRID_BOX_SUB_COLUMN_DEFS: ColumnDef<GridBoxChildGrid, unknown>[] = [
  {
    id: GRID_BOX_SUB_COLUMN_IDS.NAME,
    accessorFn: (row) => row.name,
    enableSorting: false,
    header: 'Name',
    size: 200,
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.PROJECT,
    accessorFn: (row) => row.project_name ?? '-',
    enableSorting: false,
    header: 'Project',
    size: 120,
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.SPECIMEN,
    accessorFn: (row) => (row.specimen_samples?.length > 0 ? row.specimen_samples.join(', ') : '-'),
    enableSorting: false,
    header: 'Specimen',
    size: 120,
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.POSITION,
    accessorFn: (row) => row.position_in_box ?? '-',
    enableSorting: false,
    header: 'Position',
    size: 70,
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.CLIPPED,
    accessorFn: (row) => row.clipped,
    cell: ({ row }) => <BoolIcon value={row.original.clipped} />,
    enableSorting: false,
    header: 'Clipped',
    size: 70,
    meta: { align: 'center' },
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.TRASHED,
    accessorFn: (row) => row.trashed,
    cell: ({ row }) => <BoolIcon value={row.original.trashed} />,
    enableSorting: false,
    header: 'Trashed',
    size: 70,
    meta: { align: 'center' },
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.LABELS,
    accessorFn: (row) => row.labels?.map((l) => l.name).join(', ') ?? '',
    cell: ({ row }) => <LabelChip gridId={row.original.id} labels={row.original.labels ?? []} />,
    enableSorting: false,
    header: 'Labels',
    size: 120,
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.NOTES,
    accessorFn: (row) => row.notes || '-',
    enableSorting: false,
    header: 'Notes',
    size: 220,
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.USER,
    accessorFn: (row) => row.user_name ?? '-',
    enableSorting: false,
    header: 'User',
    size: 100,
  },
  {
    id: GRID_BOX_SUB_COLUMN_IDS.CREATED,
    accessorFn: (row) => formatDate(row.create_on),
    cell: ({ row }) => formatDate(row.original.create_on),
    enableSorting: false,
    header: 'Created',
    size: 100,
  },
];
