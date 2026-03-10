'use client';

import React, { useMemo } from 'react';
import { Alert, Box, CircularProgress, TextField } from '@mui/material';
import { Button } from '@czi-sds/components';
import { DropdownSelect } from '@app/common/components/DropdownSelect';
import { CreatedSession } from '../types';
import { useSessionForm } from './useSessionForm';

interface SessionFormProps {
  onSuccess?: (session: CreatedSession) => void;
  onCancel?: () => void;
  compact?: boolean;
}

export function SessionForm({ onSuccess, onCancel, compact = false }: SessionFormProps) {
  const { state, formOptions, users, grids, magnifications, errors, isLoading, isSubmitting, updateField, submit } =
    useSessionForm();

  // Map options for DropdownSelect (needs { name } shape)
  const sessionPlanOptions = useMemo(
    () => (formOptions?.session_plans ?? []).map((sp) => ({ ...sp, name: sp.name })),
    [formOptions]
  );

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

  const selectedSessionPlan = useMemo(
    () => sessionPlanOptions.find((sp) => sp.id === state.sessionPlanId),
    [sessionPlanOptions, state.sessionPlanId]
  );

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

      <Box sx={{ '& > button': { width: '100%' } }}>
        <DropdownSelect
          topLabel="Session Plan"
          value={selectedSessionPlan}
          options={sessionPlanOptions}
          onChange={(option) => updateField('sessionPlanId', option?.id ?? null)}
        />
        {Boolean(errors.sessionPlanId) && (
          <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: '4px' }}>{errors.sessionPlanId}</Box>
        )}
      </Box>

      <Box sx={{ '& > button': { width: '100%' } }}>
        <DropdownSelect
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
          topLabel="Filter by User"
          value={selectedUser}
          options={userOptions}
          onChange={(option) => updateField('filterUserId', option?.id === 0 ? null : (option?.id ?? null))}
        />
      </Box>

      <Box sx={{ '& > button': { width: '100%' } }}>
        <DropdownSelect
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
        <div className="font-semibold">Session Name</div>
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

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 1 }}>
        {onCancel && (
          <Button sdsType="secondary" sdsStyle="rounded" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        )}
        <Button
          sdsType="primary"
          sdsStyle="rounded"
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
