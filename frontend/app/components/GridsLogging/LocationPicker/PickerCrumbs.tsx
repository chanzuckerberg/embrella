'use client';

/**
 * Crumbs: filters while browsing, the real location once a puck is open.
 *   browsing:  All dewars ▾ › All canes ▾ › My pucks ▾
 *   in a puck: Dewar A ▾ › Cane 5 ▾ › Pucks › 49 › Slot 1
 */

import React from 'react';
import { Breadcrumbs, Link, Typography } from '@mui/material';
import { Choice, FilterCrumb } from './FilterCrumb';
import { caneLabel, CRUMB } from './labels';
import { OwnerCrumb } from './OwnerCrumb';
import { PickTarget } from './types';
import { PickerNav } from './usePickerNav';

const ALL_DEWARS = 'All dewars';
const ALL_CANES = 'All canes';
const ALL = 'all';

// Clickable crumb; the last crumb is plain text.
const Crumb = ({ label, onClick }: { label: string; onClick?: () => void }) => {
  if (!onClick) return <Typography variant="body2">{label}</Typography>;

  return (
    <Link component="button" variant="body2" underline="hover" onClick={onClick}>
      {label}
    </Link>
  );
};

export const PickerCrumbs = ({ nav, userId }: { nav: PickerNav; userId: number | null }) => {
  const { nav: state, actions, dewars, canesInDewar, caneById, puck, target } = nav;

  // A box is open only for targets that pick inside boxes; EmptySlot stays on the puck.
  const boxOpen = state.slot !== null && target !== PickTarget.EmptySlot;

  // With a puck open, the dewar/cane crumbs show where it actually is.
  const dewar = puck ? nav.puckDewar : state.dewar;
  const filterCane = state.cane === null ? undefined : caneById.get(state.cane);
  const cane = puck ? nav.puckCane : filterCane;

  const dewarChoices: Choice[] = [
    { key: ALL, label: ALL_DEWARS, pick: () => actions.setDewar(null) },
    ...dewars.map((d) => ({ key: `${d.id}`, label: d.name, pick: () => actions.setDewar(d.id) })),
  ];
  const caneChoices: Choice[] = [
    { key: ALL, label: ALL_CANES, pick: () => actions.setCane(null) },
    ...canesInDewar.map((c) => ({ key: `${c.id}`, label: caneLabel(c), pick: () => actions.setCane(c.id) })),
  ];

  return (
    <Breadcrumbs separator={CRUMB} sx={{ typography: 'body2', '& .MuiBreadcrumbs-ol': { alignItems: 'center' } }}>
      <FilterCrumb label={dewar === null ? ALL_DEWARS : nav.dewarName(dewar)} choices={dewarChoices} />
      <FilterCrumb label={cane ? caneLabel(cane) : ALL_CANES} choices={caneChoices} />
      {!puck && <OwnerCrumb nav={nav} userId={userId} />}
      {puck && <Crumb label="Pucks" onClick={() => actions.openPuck(null)} />}
      {puck && <Crumb label={puck.name} onClick={boxOpen ? () => actions.openSlot(null) : undefined} />}
      {puck && boxOpen && <Crumb label={`Slot ${state.slot}`} />}
    </Breadcrumbs>
  );
};
