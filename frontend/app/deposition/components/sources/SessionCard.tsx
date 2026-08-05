'use client';

import { Icon } from '@czi-sds/components';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Autocomplete,
  Box,
  Chip,
  IconButton,
  TextField,
  Typography,
} from '@mui/material';

import type { TomogramSubsetMode } from '../../types';
import { usePlanRuns } from '../../hooks/useSources';
import { softChipSx, outlineChipSx } from './chipStyles';
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
}: {
  index: number;
  row: SourceRow;
  sessionOptions: string[];
  subsetMode: TomogramSubsetMode;
  readOnly: boolean;
  onChange: (row: SourceRow) => void;
  onRemove: () => void;
  onUploadSubset: (file: File) => void;
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

  const total = row.tomogram_total;
  const selected = rowSelected(row, subsetMode);
  const tomoBadge = total != null ? `${selected ?? '—'} / ${total} tomograms` : '— tomograms';
  const badgeWarn = subsetMode === 'custom' && !row.subset_csv_path;

  return (
    <Accordion
      defaultExpanded={index === 0}
      disableGutters
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '12px !important',
        mb: 1.5,
        overflow: 'hidden',
        '&:before': { display: 'none' },
        bgcolor: 'background.paper',
      }}
    >
      <AccordionSummary
        expandIcon={<Icon sdsIcon="ChevronDown" sdsSize="s" />}
        sx={{
          px: 2,
          minHeight: 56,
          flexDirection: 'row-reverse',
          '& .MuiAccordionSummary-content': { my: 1, alignItems: 'center', gap: 1.5, overflow: 'hidden' },
          '& .MuiAccordionSummary-expandIconWrapper': { mr: 1.5, color: 'text.secondary' },
        }}
      >
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            bgcolor: 'grey.100',
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
        <Box
          sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexShrink: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          <Chip
            size="small"
            label={tomoBadge}
            sx={softChipSx(badgeWarn ? 'warning.light' : 'grey.100', badgeWarn ? 'warning.dark' : 'text.secondary')}
          />
          {row.denoise_run_name ? (
            <Chip size="small" label="denoised" sx={softChipSx('success.light', 'success.dark')} />
          ) : null}
          {row.selected_copick_runs.length > 0 ? (
            <Chip size="small" label={`${row.selected_copick_runs.length} copick`} sx={outlineChipSx('info.main')} />
          ) : null}
          <IconButton
            size="small"
            disabled={readOnly}
            aria-label="Remove session"
            onClick={onRemove}
            sx={{ color: 'text.secondary', ml: 0.25 }}
          >
            <Icon sdsIcon="TrashCan" sdsSize="s" />
          </IconButton>
        </Box>
      </AccordionSummary>

      <AccordionDetails sx={{ px: 3, pb: 3, pt: 1 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
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
              <SubsetCsvField row={row} readOnly={readOnly} onChange={set} onUpload={onUploadSubset} />
            )}
          </Box>

          <CopickConfigs row={row} readOnly={readOnly} onChange={set} />
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}
