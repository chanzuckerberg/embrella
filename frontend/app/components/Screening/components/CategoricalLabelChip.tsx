'use client';

import { useEffect, useRef, useState } from 'react';
import { Box, Chip, ClickAwayListener, Paper, Popper, Typography } from '@mui/material';

import { API, DJANGO_URL, POST_API } from '@app/common/constants/api';
import { ScreeningLabel } from '@app/components/Screening/types';
import {
  LABEL_CATEGORIES,
  LABEL_PICKABLE,
  LabelCategory,
  labelDisplayName,
} from '@app/components/Screening/constants/labels';
import { useScreeningLabels } from '@app/components/Screening/context/ScreeningLabelsContext';

interface CategoricalLabelChipProps {
  gridId: number;
  labels: ScreeningLabel[];
  category: LabelCategory;
}

export const CategoricalLabelChip = ({ gridId, labels: initialLabels, category }: CategoricalLabelChipProps) => {
  const { getLabels, setLabels: setSharedLabels } = useScreeningLabels();
  const labels = getLabels(gridId, initialLabels);

  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ScreeningLabel[]>([]);
  const anchorRef = useRef<HTMLDivElement>(null);

  const categoryNames = LABEL_CATEGORIES[category];
  const pickableNames = LABEL_PICKABLE[category];
  const current = labels.find((l) => categoryNames.includes(l.name)) ?? null;

  useEffect(() => {
    if (!open) return;
    fetch(`${DJANGO_URL}${API.LABELS}`, { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => {
        const all: ScreeningLabel[] = Array.isArray(data) ? data : (data.results ?? []);
        const ordered = pickableNames
          .map((name) => all.find((l) => l.name === name))
          .filter((l): l is ScreeningLabel => Boolean(l));
        setOptions(ordered);
      })
      .catch(() => setOptions([]));
  }, [open, pickableNames]);

  const persist = async (next: ScreeningLabel[]) => {
    setSharedLabels(gridId, next);
    const url = `${DJANGO_URL}${POST_API.UPDATE_GRID_LABELS.replace('grid_id', String(gridId))}`;
    try {
      const res = await fetch(url, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label_ids: next.map((l) => l.id) }),
      });
      if (!res.ok) {
        // eslint-disable-next-line no-console
        console.error('Failed to update labels:', res.status, await res.text());
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('Failed to update labels:', e);
    }
  };

  const select = async (label: ScreeningLabel) => {
    setOpen(false);
    if (current && current.id === label.id) return;
    const next = [...labels.filter((l) => !categoryNames.includes(l.name)), label];
    await persist(next);
  };

  const clear = async () => {
    setOpen(false);
    if (!current) return;
    const next = labels.filter((l) => !categoryNames.includes(l.name));
    await persist(next);
  };

  return (
    <ClickAwayListener onClickAway={() => setOpen(false)}>
      <Box ref={anchorRef} onClick={(e) => e.stopPropagation()} sx={{ display: 'inline-flex' }}>
        {current ? (
          <Chip
            label={labelDisplayName(current.name)}
            size="small"
            onClick={() => setOpen((o) => !o)}
            sx={{
              backgroundColor: current.color,
              color: '#fff',
              fontWeight: 500,
              height: 22,
              fontSize: 12,
              borderRadius: '4px',
              cursor: 'pointer',
              '& .MuiChip-label': { px: '6px' },
            }}
          />
        ) : (
          <Chip
            label="+ Add"
            size="small"
            variant="outlined"
            onClick={() => setOpen((o) => !o)}
            sx={{ height: 22, fontSize: 12, borderRadius: '4px', cursor: 'pointer' }}
          />
        )}

        <Popper open={open} anchorEl={anchorRef.current} placement="bottom-start" style={{ zIndex: 1300 }}>
          <Paper elevation={3} sx={{ mt: '4px', minWidth: 140, py: 0.5 }}>
            {options.map((label) => {
              const isSelected = current?.id === label.id;
              return (
                <Box
                  key={label.id}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => select(label)}
                  sx={{
                    px: 1.5,
                    py: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    backgroundColor: isSelected ? 'action.selected' : 'transparent',
                    '&:hover': { backgroundColor: 'action.hover' },
                  }}
                >
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      backgroundColor: label.color,
                      flexShrink: 0,
                    }}
                  />
                  <Typography variant="body2">{labelDisplayName(label.name)}</Typography>
                </Box>
              );
            })}
            {current && (
              <Box
                onMouseDown={(e) => e.preventDefault()}
                onClick={clear}
                sx={{
                  px: 1.5,
                  py: '6px',
                  cursor: 'pointer',
                  borderTop: '1px solid',
                  borderColor: 'divider',
                  '&:hover': { backgroundColor: 'action.hover' },
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  Clear
                </Typography>
              </Box>
            )}
          </Paper>
        </Popper>
      </Box>
    </ClickAwayListener>
  );
};
