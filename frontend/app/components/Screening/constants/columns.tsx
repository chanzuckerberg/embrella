import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { Link as SdsLink } from '@czi-sds/components';
import { Link } from '@mui/material';
import { ColumnDef } from '@tanstack/react-table';

import { AccessorReturnType, LinkCellProps } from '@app/common/components/EntityTable/types';
import {
  getLinkPropsFromLinkField,
  getLinkCellFromCellContext,
} from '@app/common/components/EntityTable/utils/linkUtils';
import { EntityDataTypes } from '@app/common/types/tableState';
import { formatDate } from '@app/common/utils/date';
import { GridDetailIconCell } from '@app/components/GridsView/components/GridDetailIconCell';
import { useGridDetailDialog } from '@app/components/GridsView/context/GridDetailDialogContext';
import { AllLabelsCell } from '../components/AllLabelsCell';
import { CategoricalLabelChip } from '../components/CategoricalLabelChip';
import { ScreeningGridData } from '../types';

export const SCREENING_COLUMN_IDS = {
  NAME: 'name',
  PROJECT: 'project',
  STATUS: 'status',
  MICROSCOPE: 'microscope',
  PRIORITY: 'priority',
  FREEZING_SESSION: 'freezingSession',
  CLIPPED: 'clipped',
  LABELS: 'labels',
  UPDATED_AT: 'updatedAt',
  DETAILS: 'details',
};

const BoolIcon = ({ value }: { value: boolean }) =>
  value ? <CheckIcon fontSize="small" color="success" /> : <CloseIcon fontSize="small" color="disabled" />;

const NameCell = ({ row }: { row: ScreeningGridData }) => {
  const { openGridDetail } = useGridDetailDialog();
  return (
    <Link component="button" onClick={() => openGridDetail(row.grid.id)} sx={{ textAlign: 'left', fontWeight: 500 }}>
      {row.grid.name}
    </Link>
  );
};

export const SCREENING_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: SCREENING_COLUMN_IDS.NAME,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as ScreeningGridData).grid.name,
    cell: ({ row }) => <NameCell row={row.original as ScreeningGridData} />,
    enableSorting: false,
    header: 'Name',
    size: 180,
  },
  {
    id: SCREENING_COLUMN_IDS.PROJECT,
    accessorFn: (rowData: EntityDataTypes): LinkCellProps | string => {
      const { project } = rowData as ScreeningGridData;
      return project ? getLinkPropsFromLinkField(project) : '-';
    },
    cell: (props) => {
      const { project } = props.row.original as ScreeningGridData;
      if (!project) return '-';
      return getLinkCellFromCellContext(props);
    },
    enableSorting: true,
    header: 'Project',
    size: 120,
  },
  {
    id: SCREENING_COLUMN_IDS.STATUS,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as ScreeningGridData).labels.map((l) => l.name).join(','),
    cell: ({ row }) => {
      const data = row.original as ScreeningGridData;
      return <CategoricalLabelChip gridId={data.grid.id} labels={data.labels} category="status" />;
    },
    enableSorting: false,
    header: 'Status',
    size: 125,
  },
  {
    id: SCREENING_COLUMN_IDS.MICROSCOPE,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as ScreeningGridData).labels.map((l) => l.name).join(','),
    cell: ({ row }) => {
      const data = row.original as ScreeningGridData;
      return <CategoricalLabelChip gridId={data.grid.id} labels={data.labels} category="microscope" />;
    },
    enableSorting: false,
    header: 'Microscope',
    size: 75,
  },
  {
    id: SCREENING_COLUMN_IDS.PRIORITY,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as ScreeningGridData).labels.map((l) => l.name).join(','),
    cell: ({ row }) => {
      const data = row.original as ScreeningGridData;
      return <CategoricalLabelChip gridId={data.grid.id} labels={data.labels} category="priority" />;
    },
    enableSorting: true,
    header: 'Priority',
    size: 75,
  },
  {
    id: SCREENING_COLUMN_IDS.CLIPPED,
    accessorFn: (rowData: EntityDataTypes): string => String((rowData as ScreeningGridData).clipped),
    cell: ({ row }) => <BoolIcon value={(row.original as ScreeningGridData).clipped} />,
    enableSorting: false,
    header: 'Clipped',
    size: 70,
    meta: { align: 'center' },
  },
  {
    id: SCREENING_COLUMN_IDS.FREEZING_SESSION,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as ScreeningGridData).freezing_session?.name ?? '-',
    cell: ({ row }) => {
      const fs = (row.original as ScreeningGridData).freezing_session;
      if (!fs) return '-';
      return (
        <SdsLink href={fs.url} sdsStyle="default" target="_blank">
          {fs.name}
        </SdsLink>
      );
    },
    enableSorting: false,
    header: 'Freezing Session',
    size: 150,
  },
  {
    id: SCREENING_COLUMN_IDS.LABELS,
    accessorFn: (rowData: EntityDataTypes): string =>
      (rowData as ScreeningGridData).labels.map((l) => l.name).join(', '),
    cell: ({ row }) => <AllLabelsCell row={row.original as ScreeningGridData} />,
    enableSorting: false,
    header: 'All Labels',
    size: 150,
  },
  {
    id: SCREENING_COLUMN_IDS.UPDATED_AT,
    accessorFn: (rowData: EntityDataTypes): string => {
      const {
        grid: { updatedAt },
      } = rowData as ScreeningGridData;
      return !updatedAt ? '-' : formatDate(updatedAt);
    },
    enableSorting: true,
    header: 'Updated At',
    size: 100,
  },
  {
    id: SCREENING_COLUMN_IDS.DETAILS,
    accessorFn: () => '',
    cell: ({ row }) => {
      const data = row.original as ScreeningGridData;
      return <GridDetailIconCell gridId={data.grid.id} />;
    },
    enableSorting: false,
    header: '',
    size: 50,
  },
];
