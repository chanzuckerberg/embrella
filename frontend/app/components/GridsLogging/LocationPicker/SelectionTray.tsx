'use client';

/**
 * Multi mode: picks so far, one row per grid box (picks usually come by box).
 *   Cassette 8 / 12                                   Clear
 *   WT_RPE_8/26/26_B1   49 › slot 1   [1✕][2✕][3✕][4✕]   ✕
 * Position chips remove one pick (name on hover); the row ✕ removes the whole box.
 */

import React from 'react';
import { Box, Chip, IconButton, Link, Tooltip, Typography } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { pickLabel } from './labels';
import { Membership, PickedLocation } from './types';
import { Selection } from './useSelection';

const TRAY_HEIGHT = '132px';

interface BoxGroup {
  key: string;
  boxName: string;
  where: string;
  picks: PickedLocation[];
}

// Grouped by box in first-picked order; positions ascending.
const groupByBox = (picks: PickedLocation[]): BoxGroup[] => {
  const groups = new Map<string, BoxGroup>();
  for (const p of picks) {
    const key = `${p.puckId}-${p.slot}`;
    const group = groups.get(key) ?? {
      key,
      boxName: p.boxName ?? '',
      where: `${p.puckName} › slot ${p.slot}`,
      picks: [],
    };
    group.picks.push(p);
    groups.set(key, group);
  }

  return [...groups.values()].map((g) => ({
    ...g,
    picks: g.picks.sort((a, b) => (a.position ?? 0) - (b.position ?? 0)),
  }));
};

export const SelectionTray = ({ selection, title }: { selection: Selection; title: string }) => {
  const { picks, capacity, remove, clear, setMany } = selection;
  const isFull = picks.length >= capacity;

  return (
    <Box
      sx={{
        p: '12px',
        border: '1px solid',
        borderColor: 'grey.300',
        borderRadius: '4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {title} {picks.length} / {capacity}
          {isFull && (
            <Typography component="span" variant="body2" color="text.secondary">
              {' '}
              · full
            </Typography>
          )}
        </Typography>
        {picks.length > 0 && (
          <Link component="button" variant="body2" underline="hover" onClick={clear}>
            Clear
          </Link>
        )}
      </Box>

      {!picks.length && (
        <Typography variant="body2" color="text.secondary">
          Pick grids or whole boxes; they collect here.
        </Typography>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: TRAY_HEIGHT, overflowY: 'auto' }}>
        {groupByBox(picks).map((g) => (
          <Box key={g.key} sx={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="body2" noWrap title={g.boxName}>
                {g.boxName}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {g.where}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', gap: '2px', flexShrink: 0 }}>
              {g.picks.map((p) => (
                <Tooltip key={p.key} describeChild title={pickLabel(p)}>
                  <Chip size="small" label={p.position} onDelete={() => remove(p.key)} />
                </Tooltip>
              ))}
            </Box>

            <Tooltip title="Remove box">
              <IconButton
                size="small"
                aria-label={`Remove ${g.boxName}`}
                onClick={() => setMany(g.picks, Membership.Remove)}
              >
                <Icon sdsIcon="XMark" sdsSize="s" />
              </IconButton>
            </Tooltip>
          </Box>
        ))}
      </Box>
    </Box>
  );
};
