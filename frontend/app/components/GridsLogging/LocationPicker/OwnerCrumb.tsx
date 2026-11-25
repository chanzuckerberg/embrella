'use client';

/**
 * Owner crumb: scopes on top, then a type-to-filter list of other puck owners.
 *   ┌───────────────────────────┐
 *   │ ✓ My pucks                │
 *   │   Pucks with my grids     │
 *   │   All pucks               │
 *   │ ───────────────────────── │
 *   │ Others' pucks             │
 *   │ [Type a name…]            │
 *   │   User Name           7   │
 *   └───────────────────────────┘
 * Enter picks the first match. Popover, not Menu: Menu's type-to-jump would steal keystrokes.
 */

import React, { useRef, useState } from 'react';
import {
  Box,
  Divider,
  InputAdornment,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Popover,
  TextField,
  Typography,
} from '@mui/material';
import { Icon } from '@czi-sds/components';
import { CrumbTrigger } from './CrumbTrigger';
import { friendlyName, ownerLabel } from './labels';
import { Owner } from './types';
import { PickerNav } from './usePickerNav';

const WIDTH = '280px';
const PEOPLE_HEIGHT = '240px';
const CHECK_WIDTH = '28px';
const ITEM_INSET = '16px'; // MUI ListItemButton's horizontal padding
const SCOPES = [Owner.Me, Owner.MyGrids, Owner.All];
const ENTER = 'Enter';

interface Person {
  id: number;
  name: string;
  pucks: number;
}

export const OwnerCrumb = ({ nav, userId }: { nav: PickerNav; userId: number | null }) => {
  const { users, allPucks, actions } = nav;
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [term, setTerm] = useState('');
  const nameRef = useRef<HTMLInputElement>(null);

  // Other people who own pucks, with their puck count, A → Z.
  const puckCounts = new Map<number, number>();
  for (const p of allPucks) puckCounts.set(p.user, (puckCounts.get(p.user) ?? 0) + 1);

  const needle = term.trim().toLowerCase();
  const people: Person[] = users
    .filter((u) => u.id !== userId && puckCounts.has(u.id))
    .map((u) => ({ id: u.id, name: friendlyName(u), pucks: puckCounts.get(u.id) ?? 0 }))
    .filter((p) => p.name.toLowerCase().includes(needle))
    .sort((a, b) => a.name.localeCompare(b.name));

  const close = () => {
    setAnchor(null);
    setTerm('');
  };

  const pick = (owner: Owner, ownerId: number | null = null) => {
    actions.setOwner(owner, ownerId);
    close();
  };

  const isActive = (owner: Owner, ownerId: number | null = null) =>
    nav.nav.owner === owner && (owner !== Owner.Person || nav.nav.ownerId === ownerId);

  const check = (active: boolean) => (
    <ListItemIcon sx={{ minWidth: CHECK_WIDTH }}>{active && <Icon sdsIcon="Check" sdsSize="s" />}</ListItemIcon>
  );

  return (
    <>
      <CrumbTrigger label={ownerLabel(nav.nav.owner, nav.nav.ownerId, users)} onOpen={setAnchor} />

      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={close}
        // Focus the name field once visible; autoFocus fires while the grow transition still hides it.
        TransitionProps={{ onEntered: () => nameRef.current?.focus() }}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        slotProps={{ paper: { sx: { width: WIDTH } } }}
      >
        <List dense>
          {SCOPES.map((o) => (
            <ListItemButton key={o} selected={isActive(o)} onClick={() => pick(o)}>
              {check(isActive(o))}
              <ListItemText primary={ownerLabel(o, null, users)} />
            </ListItemButton>
          ))}
        </List>

        <Divider />

        {/* Heading and field share the list items' 16px left edge. */}
        <Typography variant="body2" sx={{ fontWeight: 600, px: ITEM_INSET, pt: '12px', pb: '8px' }}>
          Others&apos; pucks
        </Typography>
        <Box sx={{ px: ITEM_INSET, pb: '8px' }}>
          <TextField
            inputRef={nameRef}
            size="small"
            fullWidth
            placeholder="Type a name"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            onKeyDown={(e) => e.key === ENTER && people[0] && pick(Owner.Person, people[0].id)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Icon sdsIcon="Search" sdsSize="s" />
                </InputAdornment>
              ),
            }}
          />
        </Box>

        <List dense sx={{ maxHeight: PEOPLE_HEIGHT, overflowY: 'auto', pt: '0px' }}>
          {people.map((p) => (
            <ListItemButton key={p.id} selected={isActive(Owner.Person, p.id)} onClick={() => pick(Owner.Person, p.id)}>
              {check(isActive(Owner.Person, p.id))}
              <ListItemText primary={p.name} />
              <Typography variant="caption" color="text.secondary">
                {p.pucks}
              </Typography>
            </ListItemButton>
          ))}
          {!people.length && (
            <Typography variant="body2" color="text.secondary" sx={{ px: ITEM_INSET, py: '8px' }}>
              No one matches
            </Typography>
          )}
        </List>
      </Popover>
    </>
  );
};
