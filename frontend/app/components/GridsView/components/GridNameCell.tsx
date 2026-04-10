'use client';

import React from 'react';
import { Link } from '@czi-sds/components';
import { useGridDetailDialog } from '../context/GridDetailDialogContext';

interface GridNameCellProps {
  gridId: number;
  name: string;
}

export const GridNameCell: React.FC<GridNameCellProps> = ({ gridId, name }) => {
  const { openGridDetail } = useGridDetailDialog();

  return (
    <Link
      onClick={(e: React.MouseEvent) => {
        e.preventDefault();
        openGridDetail(gridId);
      }}
      href="#"
    >
      {name}
    </Link>
  );
};
