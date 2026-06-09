'use client';

import React from 'react';
import { Box } from '@mui/material';
import { Link } from '@czi-sds/components';
import { useGridDetailDialog } from '../context/GridDetailDialogContext';

interface GridNameCellProps {
  gridId: number;
  name: string;
  trashed?: boolean;
}

export const GridNameCell: React.FC<GridNameCellProps> = ({ gridId, name, trashed = false }) => {
  const { openGridDetail } = useGridDetailDialog();

  return (
    <Link
      onClick={(e: React.MouseEvent) => {
        e.preventDefault();
        openGridDetail(gridId);
      }}
      href="#"
    >
      <Box component="span" sx={trashed ? { opacity: 0.5, textDecoration: 'line-through' } : undefined}>
        {name}
      </Box>
    </Link>
  );
};
