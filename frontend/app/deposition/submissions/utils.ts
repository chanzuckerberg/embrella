import { alpha, type Theme } from '@mui/material/styles';

import type { ChipColor } from './constants';

export function timeAgo(iso?: string): string {
  if (!iso) return '—';
  const min = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}d ago`;
  return `${Math.floor(day / 7)}w ago`;
}

export function absDate(iso?: string): string {
  return iso ? new Date(iso).toLocaleString() : '';
}


export function softChipSx(color: ChipColor) {
  return (theme: Theme) => {
    const paletteEntry =
      color === 'default'
        ? { main: theme.palette.grey[500], dark: theme.palette.grey[700] }
        : theme.palette[color];
    return {
      backgroundColor: alpha(paletteEntry.main, 0.14),
      color: paletteEntry.dark,
      borderColor: alpha(paletteEntry.main, 0.4),
      fontWeight: 500,
    };
  };
}
