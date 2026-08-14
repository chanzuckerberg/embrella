'use client';

import { useEffect, useState } from 'react';
import { Icon } from '@czi-sds/components';
import { Autocomplete, Box, Chip, IconButton, TextField, Typography } from '@mui/material';

import type { TomogramSubsetMode } from '../../types';
import { usePlanRuns, useTomogramCount } from '../../hooks/useSources';
import { fillChipSx, outlineChipSx } from './chipStyles';
import { rowSelected } from './counts';
import { CopickConfigs } from './CopickConfigs';
import { RunSelect } from './RunSelect';
import { SubsetCsvField } from './SubsetCsvField';
import type { SourceRow } from './types';

export function SessionCard({
  index,
  row,
  sessionOptions,
  subsetMode,
  readOnly,
  onChange,
  onRemove,
  onUploadSubset,
  onCount,
}: {
  index: number;
  row: SourceRow;
  sessionOptions: string[];
  subsetMode: TomogramSubsetMode;
  readOnly: boolean;
  onChange: (row: SourceRow) => void;
  onRemove: () => void;
  onUploadSubset: (file: File) => void;
  onCount?: (key: string, total: number | undefined) => void;
}) {
  const session = row.msi_session_name;
  const aretomo = usePlanRuns('aretomo3', session);
  const denoise = usePlanRuns('denoiset', session);
  const set = (patch: Partial<SourceRow>) => onChange({ ...row, ...patch });

  const selectSession = (name: string) =>
    set({
      msi_session_name: name,
      msi_session: null,
      aretomo_run_name: '',
      denoise_run_name: '',
      selected_copick_runs: [],
    });

  const tomoCount = useTomogramCount(session, row.aretomo_run_name);
  const total = tomoCount.data;
  useEffect(() => {
    onCount?.(row.key, total);
  }, [row.key, total, onCount]);

  const rowWithCount = { ...row, tomogram_total: total };
  const selected = rowSelected(rowWithCount, subsetMode);
  const tomoBadge = total != null ? `${selected ?? '—'} / ${total} tomograms` : '— tomograms';
  const badgeWarn = selected === 0;
  const [open, setOpen] = useState(index === 0);

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        mb: 1.5,
        bgcolor: 'background.paper',
        overflow: 'hidden',
      }}
    >
      {/* Header row — chevron toggle + session identity + status chips */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 2,
          py: 1.25,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: 'grey.50',
        }}
      >
        <Box
          component="button"
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? 'Collapse session' : 'Expand session'}
          aria-expanded={open}
          sx={{
            width: 26,
            height: 26,
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            color: 'text.secondary',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            p: 0,
          }}
        >
          <Icon sdsIcon={open ? 'ChevronDown' : 'ChevronRight'} sdsSize="xs" />
        </Box>
        <Box
          sx={{
            width: 26,
            height: 26,
            borderRadius: '50%',
            bgcolor: 'grey.200',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Typography sx={{ fontWeight: 700, fontSize: '0.8125rem', color: 'text.secondary', lineHeight: 1 }}>
            {index + 1}
          </Typography>
        </Box>
        <Typography sx={{ fontWeight: 700, flex: 1, minWidth: 0, fontFamily: 'monospace' }} noWrap>
          {session || 'Select a session…'}
        </Typography>
        <Chip
          size="small"
          label={tomoBadge}
          sx={badgeWarn ? fillChipSx('warning.light', 'text.primary') : fillChipSx('grey.100', 'text.secondary')}
        />
        {row.denoise_run_name ? (
          <Chip size="small" label="denoised" sx={fillChipSx('success.light', 'success.dark')} />
        ) : null}
        {row.selected_copick_runs.length > 0 ? (
          <Chip size="small" label={`${row.selected_copick_runs.length} copick`} sx={outlineChipSx('info.main')} />
        ) : null}
        <IconButton
          size="small"
          disabled={readOnly}
          aria-label="Remove session"
          onClick={onRemove}
          sx={{ color: 'text.secondary' }}
        >
          <Icon sdsIcon="TrashCan" sdsSize="s" />
        </IconButton>
      </Box>

      {open && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, px: 3, py: 2.5 }}>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' }, gap: 2.5 }}>
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                Imaging session *
              </Typography>
              <Autocomplete
                size="small"
                disabled={readOnly}
                options={sessionOptions}
                value={session || null}
                onChange={(_, v) => selectSession(v ?? '')}
                ListboxProps={{ style: { maxHeight: 180 } }}
                renderInput={(params) => <TextField {...params} placeholder="Select session…" />}
              />
            </Box>

            <RunSelect
              label="AreTomo run"
              required
              value={row.aretomo_run_name}
              options={aretomo.data ?? []}
              loading={aretomo.isFetching}
              disabled={readOnly || !session}
              placeholder="AreTomo run"
              onChange={(v) => set({ aretomo_run_name: v })}
            />

            <RunSelect
              label="DenoisET run"
              value={row.denoise_run_name}
              options={denoise.data ?? []}
              loading={denoise.isFetching}
              disabled={readOnly || !session}
              placeholder="DenoisET run"
              allowNone
              noneLabel="None (raw tomograms)"
              onChange={(v) => set({ denoise_run_name: v })}
            />

            {subsetMode === 'custom' && (
              <Box sx={{ gridColumn: 'span 2' }}>
                <SubsetCsvField row={row} readOnly={readOnly} onChange={set} onUpload={onUploadSubset} />
              </Box>
            )}
          </Box>

          <CopickConfigs row={row} readOnly={readOnly} onChange={set} />
        </Box>
      )}
    </Box>
  );
}
