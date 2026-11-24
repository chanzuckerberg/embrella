'use client';

/**
 * Grid box style fields: size, color, numbering.
 */

import React, { useState } from 'react';
import { Box } from '@mui/material';
import { DropdownMenu, InputDropdown } from '@czi-sds/components';
import { GridLoggingChoicesResponse } from '@app/common/types/gridLogging';
import { toHex } from '@app/common/utils/color';
import { GridBoxSize } from './GridBoxSvg';
import { numberingOptions } from './gridBoxLayout';

const GRID_BOX_SIZES: GridBoxSize[] = [4, 8];

// Fields fill their grid column so edges line up across rows.
const FILL = '100%';
const MENU_MIN_WIDTH = 200;

// Keep the trigger inside its column; a value too long for it ends in "…" instead of pushing the border out.
const TRUNCATE = {
  minWidth: 0,
  '& > button': { minWidth: 0, maxWidth: '100%' },
  '& > button span': { minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
};

// SDS small icon size; outline keeps white/light colors visible.
const SWATCH_SIZE = 16;
const SWATCH_STROKE = '#999999';

// SDS InputDropdown height; text inputs next to these match it.
export const FIELD_HEIGHT = '32px';

interface Option {
  name: string;
  value: string;
  icon?: React.ReactElement;
}

interface OptionDropdownProps {
  label: string;
  options: Option[];
  value: string;
  onChange: (value: string) => void;
}

// One SDS dropdown; optional icon left of the selected name and of each option.
const OptionDropdown = ({ label, options, value, onChange }: OptionDropdownProps) => {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const selected = options.find((option) => option.value === value);

  const handleChange = (_event: React.SyntheticEvent, option: Option | null) => {
    setAnchorEl(null);
    if (!option) return;

    onChange(option.value);
  };

  return (
    <Box sx={TRUNCATE}>
      <InputDropdown
        label={label}
        sdsType="value"
        sdsStyle="square"
        width={FILL}
        value={selected?.name}
        startIcon={selected?.icon}
        state={anchorEl ? 'open' : 'default'}
        onClick={(event: React.MouseEvent<HTMLElement>) => setAnchorEl(anchorEl ? null : event.currentTarget)}
      />
      <DropdownMenu<Option, false, false, false>
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        width={Math.max(anchorEl?.clientWidth ?? 0, MENU_MIN_WIDTH)}
        options={options}
        value={selected ?? null}
        isOptionEqualToValue={(a, b) => a.value === b.value}
        onChange={handleChange}
        onClickAway={() => setAnchorEl(null)}
      />
    </Box>
  );
};

// Round color chip, e.g. "366de1" → blue dot.
const Swatch = ({ hex }: { hex: string }) => (
  <svg width={SWATCH_SIZE} height={SWATCH_SIZE} viewBox="0 0 16 16" aria-hidden>
    <circle cx="8" cy="8" r="7" fill={toHex(hex)} stroke={SWATCH_STROKE} strokeWidth="1" />
  </svg>
);

interface SizeDropdownProps {
  value: GridBoxSize;
  onChange: (size: GridBoxSize) => void;
}

export const SizeDropdown = ({ value, onChange }: SizeDropdownProps) => (
  <OptionDropdown
    label="Size"
    value={String(value)}
    onChange={(size) => onChange(Number(size) as GridBoxSize)}
    options={GRID_BOX_SIZES.map((size) => ({ name: `${size} grids`, value: String(size) }))}
  />
);

interface ColorDropdownProps {
  choices?: GridLoggingChoicesResponse;
  value: string;
  onChange: (color: string) => void;
}

export const ColorDropdown = ({ choices, value, onChange }: ColorDropdownProps) => (
  <OptionDropdown
    label="Color"
    value={value}
    onChange={onChange}
    options={(choices?.grid_box_colors ?? []).map(({ value: hex, label }) => ({
      name: label,
      value: hex,
      icon: <Swatch hex={hex} />,
    }))}
  />
);

interface NumberingDropdownProps {
  choices?: GridLoggingChoicesResponse;
  maxGrids: GridBoxSize;
  value: string;
  onChange: (numbering: string) => void;
}

// Only styles the box size supports, e.g. 8 → By column, Z-top-left.
export const NumberingDropdown = ({ choices, maxGrids, value, onChange }: NumberingDropdownProps) => (
  <OptionDropdown
    label="Numbering"
    value={value}
    onChange={onChange}
    options={numberingOptions(choices, maxGrids).map(({ value: code, label }) => ({ name: label, value: code }))}
  />
);
