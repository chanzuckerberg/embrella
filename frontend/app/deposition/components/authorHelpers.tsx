'use client';

import { Box, Chip } from '@mui/material';

import type { Person } from '../types';

export const AVATAR_COLORS = ['#6C5CE7', '#00B894', '#0984E3', '#E17055', '#E84393', '#00CEC9'];

export const personName = (p?: Person) => (p ? `${p.given_name} ${p.family_name}`.trim() : 'Unknown author');

export const initials = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('') || '?';

export const splitFullName = (full: string) => {
  const parts = full.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { given_name: '', family_name: '' };
  if (parts.length === 1) return { given_name: parts[0], family_name: '' };
  return { given_name: parts[0], family_name: parts.slice(1).join(' ') };
};

export function RoleChip({ kind }: { kind: 'P' | 'C' }) {
  const primary = kind === 'P';
  return (
    <Box
      component="span"
      aria-label={primary ? 'Primary' : 'Corresponding'}
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 18,
        height: 18,
        flexShrink: 0,
        borderRadius: '4px',
        fontWeight: 700,
        fontSize: 11,
        lineHeight: 1,
        bgcolor: (t) => `${primary ? t.palette.primary.main : t.palette.success.main}24`,
        color: primary ? 'primary.main' : 'success.dark',
      }}
    >
      {kind}
    </Box>
  );
}

export function RolePill({ kind }: { kind: 'primary' | 'corresponding' }) {
  const primary = kind === 'primary';
  return (
    <Chip
      label={primary ? 'Primary' : 'Corresponding'}
      size="small"
      sx={{
        height: 22,
        fontWeight: 600,
        fontSize: 12,
        bgcolor: (t) => `${primary ? t.palette.primary.main : t.palette.success.main}24`,
        color: primary ? 'primary.main' : 'success.dark',
      }}
    />
  );
}
