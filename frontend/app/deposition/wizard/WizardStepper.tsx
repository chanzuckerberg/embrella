'use client';

import { Fragment } from 'react';
import CheckIcon from '@mui/icons-material/Check';
import { alpha, Box, Typography, type SxProps, type Theme } from '@mui/material';

import type { StepDef } from './wizardTypes';

type StepState = 'current' | 'done' | 'todo' | 'skipped';

function stepState(num: number, current: number, isSkipped: boolean): StepState {
  if (isSkipped) return 'skipped';
  if (num === current) return 'current';
  if (num < current) return 'done';
  return 'todo';
}

const CIRCLE_SX: Record<StepState, SxProps<Theme>> = {
  current: {
    bgcolor: 'primary.main',
    color: 'primary.contrastText',
    borderColor: 'primary.main',
    boxShadow: (theme) => `0 0 0 4px ${alpha(theme.palette.primary.main, 0.22)}`,
  },
  done: { bgcolor: 'primary.main', color: 'primary.contrastText', borderColor: 'primary.main' },
  todo: { bgcolor: 'background.paper', color: 'text.secondary', borderColor: 'divider' },
  skipped: { bgcolor: 'action.disabledBackground', color: 'text.disabled', borderColor: 'divider' },
};

const LABEL_COLOR: Record<StepState, string> = {
  current: 'text.primary',
  done: 'text.secondary',
  todo: 'text.secondary',
  skipped: 'text.disabled',
};

export function WizardStepper({
  steps,
  current,
  onSelect,
  skipped = [],
}: {
  steps: StepDef[];
  current: number;
  onSelect: (num: number) => void;
  skipped?: number[];
}) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
      {steps.map((s, i) => {
        const isSkipped = skipped.includes(s.num);
        const state = stepState(s.num, current, isSkipped);
        return (
          <Fragment key={s.num}>
            {i > 0 && (
              <Box
                aria-hidden
                sx={{
                  flex: 1,
                  height: 2,
                  mt: '19px',
                  mx: 1.5,
                  borderRadius: 1,
                  bgcolor: s.num <= current ? 'primary.main' : 'divider',
                }}
              />
            )}
            <Box
              sx={{ flexShrink: 0, width: 112, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}
            >
              <Box
                component="button"
                type="button"
                onClick={() => !isSkipped && onSelect(s.num)}
                disabled={isSkipped}
                aria-label={`Step ${s.num}: ${s.title}${isSkipped ? ' (skipped)' : ''}`}
                aria-current={state === 'current' ? 'step' : undefined}
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  border: '1px solid',
                  cursor: isSkipped ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 15,
                  fontWeight: 600,
                  p: 0,
                  transition: 'background-color 120ms, box-shadow 120ms, border-color 120ms',
                  ...CIRCLE_SX[state],
                }}
              >
                {state === 'done' ? <CheckIcon sx={{ fontSize: 20 }} /> : s.num}
              </Box>
              <Typography
                variant="caption"
                sx={{
                  textAlign: 'center',
                  lineHeight: 1.25,
                  color: LABEL_COLOR[state],
                  fontWeight: state === 'current' ? 700 : 400,
                }}
              >
                {s.title}
              </Typography>
            </Box>
          </Fragment>
        );
      })}
    </Box>
  );
}
