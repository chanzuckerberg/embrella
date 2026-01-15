import { Chip } from '@mui/material';

import { DirectoryOrigin, ORIGIN_COLORS, ORIGIN_LABELS } from '../types';

interface OriginBadgeProps {
  origin: DirectoryOrigin;
}

/**
 * Color-coded badge displaying the origin classification of a directory.
 */
export const OriginBadge = ({ origin }: OriginBadgeProps) => {
  const color = ORIGIN_COLORS[origin] || ORIGIN_COLORS.unknown;
  const label = ORIGIN_LABELS[origin] || origin;

  return (
    <Chip
      label={label}
      size="small"
      sx={{
        backgroundColor: color,
        color: '#fff',
        fontWeight: 500,
        fontSize: '0.75rem',
      }}
    />
  );
};
