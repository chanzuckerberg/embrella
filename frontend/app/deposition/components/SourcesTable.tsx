'use client';

import { Button, Callout, Icon } from '@czi-sds/components';
import { Box, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';

import type { TomogramSubsetMode } from '../types';
import { rollup } from './sources/counts';
import { DepositionSummary } from './sources/DepositionSummary';
import { SessionCard } from './sources/SessionCard';
import type { SourceRow } from './sources/types';

export type { SourceRow } from './sources/types';

function modeHelp(mode: TomogramSubsetMode, excluded: number): string {
  if (mode === 'all') return 'Every tomogram from each selected AreTomo run is deposited.';
  if (mode === 'custom') return 'Set a Subset CSV on each session below - upload a file or point at a cluster path.';
  if (excluded > 0) {
    return `Filtered against copick ExperimentRuns - ${excluded} tomograms without annotations are excluded.`;
  }
  return 'Filtered against copick ExperimentRuns - tomograms without annotations are excluded.';
}

const emptyRow = (key: string): SourceRow => ({
  key,
  msi_session: null,
  msi_session_name: '',
  aretomo_run_name: '',
  denoise_run_name: '',
  subset_csv_path: '',
  selected_copick_runs: [],
});

export function SourcesTable({
  rows,
  sessionOptions,
  subsetMode,
  readOnly,
  onChange,
  onSubsetModeChange,
  onUploadSubset,
}: {
  rows: SourceRow[];
  sessionOptions: string[];
  subsetMode: TomogramSubsetMode;
  readOnly: boolean;
  onChange: (rows: SourceRow[]) => void;
  onSubsetModeChange: (v: TomogramSubsetMode) => void;
  onUploadSubset: (row: SourceRow, file: File) => void;
}) {
  const updateRow = (key: string, next: SourceRow) => onChange(rows.map((r) => (r.key === key ? next : r)));
  const removeRow = (key: string) => onChange(rows.filter((r) => r.key !== key));
  const addRow = () => onChange([...rows, emptyRow(`new-${rows.length}-${sessionOptions.length}`)]);

  const stats = rollup(rows, subsetMode);
  const sessionLabel = `${stats.sessions} session${stats.sessions === 1 ? '' : 's'}`;
  const headerStats =
    stats.totalTomograms > 0 ? `${sessionLabel} · ${stats.selectedTomograms} tomograms selected` : sessionLabel;
  const allLabel = stats.totalTomograms > 0 ? `All ${stats.totalTomograms}` : 'All';
  const annotatedLabel = stats.annotatedTomograms > 0 ? `Annotated only ${stats.annotatedTomograms}` : 'Annotated only';

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 1fr) 260px' },
        gap: 3,
        alignItems: 'start',
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 2,
            mb: 1,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', gap: 1.5 }}>
            <Typography
              variant="overline"
              sx={{ fontWeight: 700, letterSpacing: 1.2, color: 'text.secondary', lineHeight: 1.2 }}
            >
              Imaging sessions
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {headerStats}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1.25 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.secondary' }}>
              Deposit
            </Typography>
            <ToggleButtonGroup
              exclusive
              size="small"
              value={subsetMode}
              onChange={(_, v: TomogramSubsetMode | null) => v && onSubsetModeChange(v)}
              disabled={readOnly}
              sx={{
                bgcolor: 'grey.100',
                p: 0.35,
                '& .MuiToggleButtonGroup-grouped': {
                  border: 0,
                  textTransform: 'none',
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  px: 1.75,
                  py: 0.5,
                  color: 'text.secondary',
                  '&.Mui-selected': {
                    bgcolor: 'primary.main',
                    color: 'primary.contrastText',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.12)',
                    '&:hover': { bgcolor: 'primary.dark' },
                  },
                },
              }}
            >
              <ToggleButton value="all">{allLabel}</ToggleButton>
              <ToggleButton value="annotated">{annotatedLabel}</ToggleButton>
              <ToggleButton value="custom">Custom CSV</ToggleButton>
            </ToggleButtonGroup>
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
          {modeHelp(subsetMode, stats.totalTomograms - stats.selectedTomograms)}
        </Typography>

        {rows.length === 0 && (
          <Callout intent="info" sdsStyle="persistent">
            No sessions yet. Add the imaging sessions this dataset was built from.
          </Callout>
        )}

        {rows.map((row, i) => (
          <SessionCard
            key={row.key}
            index={i}
            row={row}
            sessionOptions={sessionOptions}
            subsetMode={subsetMode}
            readOnly={readOnly}
            onChange={(next) => updateRow(row.key, next)}
            onRemove={() => removeRow(row.key)}
            onUploadSubset={(file) => onUploadSubset(row, file)}
          />
        ))}

        {!readOnly && (
          <Button
            sdsType="primary"
            sdsStyle="outline"
            startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
            onClick={addRow}
            sx={{ mt: 0.5, textTransform: 'none', fontWeight: 600 }}
          >
            Add another session
          </Button>
        )}
      </Box>

      <Box sx={{ display: { xs: 'none', md: 'block' } }}>
        <DepositionSummary rows={rows} subsetMode={subsetMode} />
      </Box>
    </Box>
  );
}
