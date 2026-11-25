'use client';

/**
 * Crumb that filters by one of a few choices, e.g. "All dewars ▾" → All dewars / Dewar A / Dewar B.
 */

import React, { useState } from 'react';
import { Menu, MenuItem } from '@mui/material';
import { CrumbTrigger } from './CrumbTrigger';

export interface Choice {
  key: string;
  label: string;
  pick: () => void;
}

export const FilterCrumb = ({ label, choices }: { label: string; choices: Choice[] }) => {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  return (
    <>
      <CrumbTrigger label={label} onOpen={setAnchor} />
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {choices.map((c) => (
          <MenuItem
            key={c.key}
            onClick={() => {
              setAnchor(null);
              c.pick();
            }}
          >
            {c.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};
