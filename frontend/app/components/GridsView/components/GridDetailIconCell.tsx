'use client';

import React from 'react';
import { IconButton } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { useGridDetailDialog } from '../context/GridDetailDialogContext';

interface GridDetailIconCellProps {
  gridId: number;
}

export const GridDetailIconCell: React.FC<GridDetailIconCellProps> = ({ gridId }) => {
  const { openGridDetail } = useGridDetailDialog();

  return (
    <IconButton
      size="small"
      onClick={() => openGridDetail(gridId)}
      sx={{ color: 'text.secondary', '&:hover': { color: 'primary.main' } }}
    >
      <Icon sdsIcon="InfoCircle" sdsSize="s" />
    </IconButton>
  );
};
