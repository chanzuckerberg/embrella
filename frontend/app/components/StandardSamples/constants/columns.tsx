import { ColumnDef } from '@tanstack/react-table';

import { EntityDataTypes } from '@app/common/types/tableState';
import { AccessorReturnType } from '@app/common/components/EntityTable/types';
import { StandardSampleData } from '../types';

export const STANDARD_SAMPLE_COLUMN_IDS = {
  SPECIMEN: 'specimen',
  AVAILABLE_GRID_COUNT: 'availableGridCount',
  POINT_OF_CONTACT: 'pointOfContact',
};

export const STANDARD_SAMPLE_COLUMN_DEFS: ColumnDef<EntityDataTypes, AccessorReturnType>[] = [
  {
    id: STANDARD_SAMPLE_COLUMN_IDS.SPECIMEN,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as StandardSampleData).specimen.name,
    enableSorting: false,
    header: 'Specimen',
    size: 75,
  },
  {
    id: STANDARD_SAMPLE_COLUMN_IDS.AVAILABLE_GRID_COUNT,
    accessorFn: (rowData: EntityDataTypes): string => String((rowData as StandardSampleData).availableGridCount),
    enableSorting: true,
    header: '# Available Grids',
    size: 40,
  },
  {
    id: STANDARD_SAMPLE_COLUMN_IDS.POINT_OF_CONTACT,
    accessorFn: (rowData: EntityDataTypes): string => (rowData as StandardSampleData).pointOfContact ?? '-',
    enableSorting: false,
    header: 'Point of Contact',
    size: 200,
  },
];
