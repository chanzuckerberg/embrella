'use client';

/**
 * Under a narrowed puck list, offer the wider scopes:
 *   "Not here? Show pucks with my grids · all pucks"
 */

import React from 'react';
import { Link, Typography } from '@mui/material';
import { Owner } from './types';
import { PickerNav } from './usePickerNav';

const WIDER: Record<Owner, Owner[]> = {
  [Owner.Me]: [Owner.MyGrids, Owner.All],
  [Owner.MyGrids]: [Owner.All],
  [Owner.Person]: [Owner.All],
  [Owner.All]: [],
};

const LINK_TEXT: Record<Owner, string> = {
  [Owner.Me]: 'my pucks',
  [Owner.MyGrids]: 'pucks with my grids',
  [Owner.All]: 'all pucks',
  [Owner.Person]: '',
};

export const NotHere = ({ nav }: { nav: PickerNav }) => {
  const wider = WIDER[nav.nav.owner];
  if (!wider.length) return null;

  return (
    <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
      Not here? Show{' '}
      {wider.map((o, i) => (
        <React.Fragment key={o}>
          {i > 0 && ' · '}
          {/* Button-links default to vertical-align: middle; baseline keeps them on the sentence's line. */}
          <Link
            component="button"
            variant="body2"
            underline="hover"
            onClick={() => nav.actions.setOwner(o)}
            sx={{ verticalAlign: 'baseline' }}
          >
            {LINK_TEXT[o]}
          </Link>
        </React.Fragment>
      ))}
    </Typography>
  );
};
