'use client';

/**
 * Pucks under cane headers, one stacked row each; the puck name leads.
 *   Cane 3
 *   (◉) 21 : XLPP
 *       User Name · 5 boxes
 * Owner shows only when the scope mixes owners; slot targets count free slots instead of boxes.
 */

import React from 'react';
import { Box, Typography } from '@mui/material';
import { PuckSVG } from '@app/components/GridsLogging/Pucks/PuckSvg';
import { PuckList as Puck } from '@app/common/types/gridLogging';
import { boxesLabel, caneLabel } from './labels';
import { Owner, PickTarget } from './types';
import { PickerNav } from './usePickerNav';

const THUMB = 40;
const LIST_HEIGHT = '420px';

const freeLabel = (p: Puck) => {
  const free = p.max_boxes - p.grid_box_count;
  return `${free} free slot${free === 1 ? '' : 's'}`;
};

interface PuckRowProps {
  puck: Puck;
  detail: string;
  owner?: string;
  onClick: () => void;
}

const PuckRow = ({ puck, detail, owner, onClick }: PuckRowProps) => (
  <Box
    component="button"
    onClick={onClick}
    title={owner}
    sx={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      width: '100%',
      px: '8px',
      py: '4px',
      border: 'none',
      background: 'none',
      textAlign: 'left',
      cursor: 'pointer',
      borderRadius: '4px',
      '&:hover, &:focus-visible': { bgcolor: 'grey.100' },
    }}
  >
    <PuckSVG puck={puck} size={THUMB} disableSlotClick />
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="body1" noWrap sx={{ fontWeight: 600 }}>
        {puck.name}
      </Typography>
      <Typography variant="caption" color="text.secondary" noWrap component="div">
        {[owner, detail].filter(Boolean).join(' · ')}
      </Typography>
    </Box>
  </Box>
);

export const PuckList = ({ nav, userId }: { nav: PickerNav; userId: number | null }) => {
  const { pucks, caneById, actions } = nav;

  if (!pucks.length) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: '24px' }}>
        No pucks match
      </Typography>
    );
  }

  const showOwner = nav.nav.owner === Owner.All || nav.nav.owner === Owner.MyGrids;
  const detailOf = nav.target === PickTarget.EmptySlot ? freeLabel : boxesLabel;

  const groups = new Map<string, Puck[]>();
  for (const p of pucks) {
    const title = caneLabel(caneById.get(p.cane));
    groups.set(title, [...(groups.get(title) ?? []), p]);
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: LIST_HEIGHT, overflowY: 'auto' }}>
      {[...groups.entries()].map(([title, group]) => (
        <Box key={title}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
          {group.map((p) => (
            <PuckRow
              key={p.id}
              puck={p}
              detail={detailOf(p)}
              owner={showOwner && p.user !== userId ? nav.nameOf(p.user) : undefined}
              onClick={() => actions.openPuck(p.id)}
            />
          ))}
        </Box>
      ))}
    </Box>
  );
};
