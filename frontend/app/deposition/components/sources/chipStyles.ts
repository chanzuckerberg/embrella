import type { SxProps, Theme } from '@mui/material';

const BASE = {
  height: 24,
  fontWeight: 600,
  fontSize: '0.75rem',
  '& .MuiChip-label': { px: 1.25 },
} as const;

export function fillChipSx(bg: string, color: string): SxProps<Theme> {
  return { ...BASE, bgcolor: bg, color, border: 'none' };
}

export function outlineChipSx(color: string): SxProps<Theme> {
  return { ...BASE, bgcolor: 'transparent', color, border: '1px solid', borderColor: color };
}
