'use client';

/**
 * Breadcrumb that opens a menu, e.g. "All dewars ▾"; the parent owns the menu.
 */

import React from 'react';
import { Link } from '@mui/material';
import { Icon } from '@czi-sds/components';

interface CrumbTriggerProps {
  label: string;
  onOpen: (anchor: HTMLElement) => void;
}

export const CrumbTrigger = ({ label, onOpen }: CrumbTriggerProps) => (
  <Link
    component="button"
    variant="body2"
    underline="hover"
    onClick={(e: React.MouseEvent<HTMLElement>) => onOpen(e.currentTarget)}
    sx={{ display: 'inline-flex', alignItems: 'center', gap: '2px' }}
  >
    {label}
    <Icon sdsIcon="ChevronDown" sdsSize="xs" />
  </Link>
);
