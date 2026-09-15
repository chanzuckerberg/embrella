'use client';

import React, { useMemo } from 'react';
import { Alert, alpha, Box, CircularProgress, SxProps, TextField, Theme } from '@mui/material';
import {
  Accordion,
  AccordionDetails,
  AccordionHeader,
  Button,
  InputToggle,
  SegmentedControl,
} from '@czi-sds/components';
import { DropdownSelect } from '@app/common/components/DropdownSelect';
import { primary100, primary500 } from '@app/common/theme';
import { CreatedSession, PLAN_TIERS, PlanTier } from '../types';
import { useSessionForm } from './useSessionForm';

const LABEL_INDENT_CLASS = 'pl-4';
// DropdownSelect adds font-semibold itself; plain labels need both.
const LABEL_CLASS = `font-semibold ${LABEL_INDENT_CLASS}`;

const PLAN_TIER_LABELS: Record<PlanTier, string> = {
  scope: 'Microscope',
  software: 'Software',
  workflow: 'Workflow',
  camera: 'Camera',
};

const SEGMENT_STYLES: SxProps<Theme> = {
  '& .MuiToggleButtonGroup-root': {
    backgroundColor: (theme) => primary100({ theme }),
    overflow: 'hidden',
    '&, &:hover': { boxShadow: (theme) => `inset 0 0 0 1px ${alpha(primary500({ theme }) ?? '#000', 0.25)}` },
    '&:has(.Mui-disabled)': { backgroundColor: 'grey.100', boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.12)' },

    '& .MuiToggleButton-root': {
      backgroundColor: 'transparent',
      color: 'text.primary',
      fontSize: '0.875rem',
      lineHeight: 1.4,
      padding: '4px 14px',
      '& *': { fontSize: 'inherit', lineHeight: 'inherit' },
      '&:hover': { backgroundColor: (theme) => alpha(primary500({ theme }) ?? '#000', 0.12) },
      '&.Mui-disabled': { color: 'text.disabled' },
    },
    '& .MuiToggleButton-root.Mui-selected, & .MuiToggleButton-root.Mui-selected:hover': {
      backgroundColor: 'common.white',
      color: (theme) => primary500({ theme }),
      fontWeight: 600,
      boxShadow: '0 1px 2px rgba(0,0,0,0.15)',
    },
  },
};

interface SessionFormProps {
  onSuccess?: (session: CreatedSession) => void;
  onCancel?: () => void;
  compact?: boolean;
}

export function SessionForm({ onSuccess, onCancel, compact = false }: SessionFormProps) {
  const {
    state,
    formOptions,
    users,
    grids,
    magnifications,
    errors,
    isLoading,
    isSubmitting,
    planSelection,
    planTierOptions,
    updateField,
    selectPlanTier,
    selectFilterUser,
    submit,
  } = useSessionForm();

  const projectOptions = useMemo(
    () => (formOptions?.projects ?? []).map((p) => ({ ...p, name: p.name })),
    [formOptions]
  );

  const userOptions = useMemo(
    () => [
      { id: 0, name: 'All Users' },
      ...users.map((u) => ({
        id: u.id,
        name: u.full_name || u.username || `${u.first_name ?? ''} ${u.last_name ?? ''}`.trim(),
      })),
    ],
    [users]
  );

  const gridOptions = useMemo(() => grids.map((g) => ({ ...g, name: g.display_name || g.name })), [grids]);

  const selectedProject = useMemo(
    () => projectOptions.find((p) => p.id === state.projectId),
    [projectOptions, state.projectId]
  );

  const selectedUser = useMemo(
    () => userOptions.find((u) => u.id === (state.filterUserId ?? 0)),
    [userOptions, state.filterUserId]
  );

  const selectedGrid = useMemo(() => gridOptions.find((g) => g.id === state.gridId), [gridOptions, state.gridId]);

  const magnificationOptions = useMemo(() => magnifications.map((m) => ({ ...m, name: m.display })), [magnifications]);

  const selectedMagnification = useMemo(
    () => magnificationOptions.find((m) => m.id === state.magnificationId),
    [magnificationOptions, state.magnificationId]
  );

  const handleSubmit = async () => {
    const session = await submit();
    if (session && onSuccess) {
      onSuccess(session);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: compact ? 2 : 3 }}>
      {Boolean(errors.submit) && <Alert severity="error">{errors.submit}</Alert>}

      {/* The session plan, one tier at a time: microscope -> software -> workflow -> camera.
          Every option is on screen as a segment, so each tier is one click. */}
      {PLAN_TIERS.map((tier, index) => {
        const previousTier = PLAN_TIERS[index - 1];
        return (
          <Box key={tier} sx={SEGMENT_STYLES}>
            <div className={LABEL_CLASS}>{PLAN_TIER_LABELS[tier]}</div>
            <SegmentedControl
              aria-label={PLAN_TIER_LABELS[tier]}
              buttonDefinition={planTierOptions[tier].map((value) => ({
                label: value,
                shouldShowTooltip: false,
                value,
              }))}
              value={planSelection[tier] ?? null}
              disabled={Boolean(previousTier) && !planSelection[previousTier]}
              onChange={(_event, value) => selectPlanTier(tier, value ?? undefined)}
            />
          </Box>
        );
      })}
      {Boolean(errors.sessionPlanId) && (
        <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: '-12px' }}>{errors.sessionPlanId}</Box>
      )}

      <Box sx={{ '& > button': { width: '100%' } }}>
        <DropdownSelect
          topLabelClass={LABEL_INDENT_CLASS}
          topLabel="Project"
          value={selectedProject}
          options={projectOptions}
          onChange={(option) => updateField('projectId', option?.id ?? null)}
        />
        {Boolean(errors.projectId) && (
          <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: '4px' }}>{errors.projectId}</Box>
        )}
      </Box>

      <Box sx={{ '& > button': { width: '100%' } }}>
        <DropdownSelect
          topLabelClass={LABEL_INDENT_CLASS}
          topLabel="Filter by User"
          value={selectedUser}
          options={userOptions}
          onChange={(option) => selectFilterUser(option?.id === 0 ? null : (option?.id ?? null))}
        />
      </Box>

      <Box sx={{ '& > button': { width: '100%' } }}>
        <DropdownSelect
          topLabelClass={LABEL_INDENT_CLASS}
          topLabel="Grid"
          value={selectedGrid}
          options={gridOptions}
          onChange={(option) => updateField('gridId', option?.id ?? null)}
        />
        {Boolean(errors.gridId) && (
          <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: '4px' }}>{errors.gridId}</Box>
        )}
      </Box>

      <Box sx={{ '& > button': { width: '100%' } }}>
        <DropdownSelect
          topLabelClass={LABEL_INDENT_CLASS}
          topLabel="Magnification"
          value={selectedMagnification}
          options={magnificationOptions}
          onChange={(option) => updateField('magnificationId', option?.id ?? null)}
        />
        {Boolean(errors.magnificationId) && (
          <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: '4px' }}>{errors.magnificationId}</Box>
        )}
      </Box>

      <Box>
        <div className={LABEL_CLASS}>Session Name</div>
        <TextField
          value={state.name}
          onChange={(e) => updateField('name', e.target.value)}
          placeholder="e.g. 26mar05a"
          size="small"
          fullWidth
          error={Boolean(errors.name)}
          helperText={errors.name}
          inputProps={{ maxLength: 20 }}
          sx={{ mt: '4px' }}
        />
      </Box>

      {/* Accessory acquisition parameters, prefilled from the plan's profile. Collapsed: they rarely change. */}
      <Accordion id="session-other-settings" togglePosition="left">
        <AccordionHeader>Other Settings</AccordionHeader>
        <AccordionDetails>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <InputToggle
              checked={state.superResolution}
              onChange={() => updateField('superResolution', !state.superResolution)}
            />
            <span>Super-resolution frames</span>
          </Box>
        </AccordionDetails>
      </Accordion>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 1 }}>
        {onCancel && (
          <Button sdsType="secondary" sdsStyle="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        )}
        <Button
          sdsType="primary"
          sdsStyle="solid"
          onClick={handleSubmit}
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={16} /> : undefined}
        >
          {isSubmitting ? 'Creating...' : 'Create Session'}
        </Button>
      </Box>
    </Box>
  );
}
