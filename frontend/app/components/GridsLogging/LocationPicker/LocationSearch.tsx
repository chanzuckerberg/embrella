'use client';

/**
 * Search box: puck names from the loaded list, box/grid names from the inventory search.
 *   "Grid · 49 › slot 1 › pos 4" · "Box · 49 › slot 1" · "Puck · User Name"
 *   Grid target, single: a grid hit picks it and opens its box.
 *   Grid target, multi:  a grid hit toggles it; results stay open to add several.
 *   Other targets:       hits only navigate.
 *   Trashed grids (with onPickTrashed): inventory search with status Trashed, own section
 *   below live hits, always shown on a match since live and trashed grids often share names.
 */

import React, { useState } from 'react';
import {
  Box,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  ListSubheader,
  Paper,
  TextField,
} from '@mui/material';
import { Icon } from '@czi-sds/components';
import { CRUMB } from './labels';
import { PickedLocation, PickTarget, SelectMode, TrashedGrid } from './types';
import { HitKind, SearchHit, useLocationSearch } from './useLocationSearch';
import { useTrashedSearch } from './useTrashedSearch';
import { PickerNav } from './usePickerNav';
import { Selection } from './useSelection';

const RESULTS_HEIGHT = '280px';
const PLACEHOLDER = 'Search grid, box or puck';
const PLACEHOLDER_TRASHED = `${PLACEHOLDER} (incl. trashed grids)`;

const hitDetail = (h: SearchHit) =>
  h.kind === HitKind.Grid
    ? `Grid · ${h.puckName} ${CRUMB} slot ${h.slot} ${CRUMB} pos ${h.position}`
    : `Box · ${h.puckName} ${CRUMB} slot ${h.slot}`;

const toPick = (h: SearchHit): PickedLocation | null => {
  if (h.gridId === undefined) return null;

  return {
    key: `g${h.gridId}`,
    puckId: h.puckId,
    puckName: h.puckName,
    slot: h.slot,
    gridBoxId: h.gridBoxId,
    boxName: h.boxName,
    position: h.position,
    gridId: h.gridId,
    gridName: h.label,
  };
};

interface LocationSearchProps {
  nav: PickerNav;
  selection: Selection;
  canPick: (pick: PickedLocation) => boolean;
  onPickTrashed?: (grid: TrashedGrid) => void;
}

export const LocationSearch = ({ nav, selection, canPick, onPickTrashed }: LocationSearchProps) => {
  const { actions, allPucks, target } = nav;
  const [term, setTerm] = useState('');
  const boxHits = useLocationSearch(term);
  const isMulti = selection.mode === SelectMode.Multi;

  const needle = term.trim().toLowerCase();
  const puckHits = needle ? allPucks.filter((p) => p.name.toLowerCase().includes(needle)) : [];
  const trashedHits = useTrashedSearch(term, onPickTrashed !== undefined);

  const done = () => setTerm('');

  const pickHit = (hit: SearchHit) => {
    const pick = target === PickTarget.Grid ? toPick(hit) : null;

    // Navigate only: box hits, non-grid targets, grids this picker won't take.
    if (!pick || !canPick(pick)) {
      actions.jumpTo(hit.puckId, hit.slot);
      done();
      return;
    }

    selection.toggle(pick);
    if (isMulti) return;

    actions.jumpTo(hit.puckId, hit.slot);
    done();
  };

  return (
    <Box sx={{ position: 'relative' }}>
      <TextField
        size="small"
        fullWidth
        placeholder={onPickTrashed ? PLACEHOLDER_TRASHED : PLACEHOLDER}
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Icon sdsIcon="Search" sdsSize="s" />
            </InputAdornment>
          ),
        }}
      />

      {/* Results float over the content below. */}
      {needle && (
        <Paper
          elevation={4}
          sx={{
            position: 'absolute',
            zIndex: 2,
            left: 0,
            right: 0,
            mt: '4px',
            maxHeight: RESULTS_HEIGHT,
            overflowY: 'auto',
          }}
        >
          <List dense>
            {puckHits.map((p) => (
              <ListItemButton
                key={`p${p.id}`}
                onClick={() => {
                  actions.openPuck(p.id);
                  done();
                }}
              >
                <ListItemText primary={p.name} secondary={`Puck · ${nav.nameOf(p.user)}`} />
              </ListItemButton>
            ))}
            {boxHits.map((h) => {
              const pick = toPick(h);
              const picked = isMulti && pick !== null && selection.isPicked(pick.key);

              return (
                <ListItemButton key={h.key} onClick={() => pickHit(h)}>
                  <ListItemText primary={h.label} secondary={hitDetail(h)} />
                  {picked && <Icon sdsIcon="Check" sdsSize="s" />}
                </ListItemButton>
              );
            })}
            {trashedHits.length > 0 && <ListSubheader>Trashed</ListSubheader>}
            {trashedHits.map((g) => (
              <ListItemButton key={`t${g.id}`} onClick={() => onPickTrashed?.(g)}>
                <ListItemText
                  primary={g.name}
                  secondary={g.detail}
                  primaryTypographyProps={{ color: 'text.secondary' }}
                />
              </ListItemButton>
            ))}
            {!puckHits.length && !boxHits.length && !trashedHits.length && (
              <ListItemText sx={{ px: '16px', color: 'text.secondary' }} primary="No matches" />
            )}
          </List>
        </Paper>
      )}
    </Box>
  );
};
