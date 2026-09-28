'use client';

import { useCallback, useState } from 'react';
import { Button, Callout, Icon } from '@czi-sds/components';
import { Box, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';

import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';

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
  const [pendingRemoval, setPendingRemoval] = useState<SourceRow | null>(null);
  const removeRow = (row: SourceRow) => {
    if (row.id != null) setPendingRemoval(row);
    else onChange(rows.filter((r) => r.key !== row.key));
  };
  const [pendingSessionChange, setPendingSessionChange] = useState<SourceRow | null>(null);
  // pendingSessionChange is the replacement row, the title names the session it replaces.
  const changingFrom = pendingSessionChange
    ? rows.find((r) => r.key === pendingSessionChange.key)?.msi_session_name
    : undefined;
  const addRow = () => onChange([...rows, emptyRow(`new-${rows.length}-${sessionOptions.length}`)]);

  const [counts, setCounts] = useState<Record<string, number | undefined>>({});
  const reportCount = useCallback((key: string, total: number | undefined) => {
    setCounts((c) => (c[key] === total ? c : { ...c, [key]: total }));
  }, []);
  const [annotatedCounts, setAnnotatedCounts] = useState<Record<string, number | undefined>>({});
  const reportAnnotated = useCallback((key: string, count: number | undefined) => {
    setAnnotatedCounts((c) => (c[key] === count ? c : { ...c, [key]: count }));
  }, []);
  const rowsWithCounts = rows.map((r) => ({
    ...r,
    tomogram_total: counts[r.key],
    tomogram_selected: annotatedCounts[r.key],
  }));

  const stats = rollup(rowsWithCounts, subsetMode);
  const sessionLabel = `${stats.sessions} session${stats.sessions === 1 ? '' : 's'}`;
  const selectedText = stats.selectedKnown ? `${stats.selectedTomograms}` : '-';
  const headerStats = stats.totalTomograms > 0 ? `${sessionLabel} · ${selectedText} tomograms selected` : sessionLabel;
  const excluded = stats.selectedKnown ? stats.totalTomograms - stats.selectedTomograms : 0;
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
      <ConfirmDialog
        open={pendingRemoval !== null}
        onClose={() => setPendingRemoval(null)}
        onConfirm={() => {
          if (pendingRemoval) onChange(rows.filter((r) => r.key !== pendingRemoval.key));
          setPendingRemoval(null);
        }}
        intent="danger"
        title={
          pendingRemoval?.msi_session_name ? `Remove session ${pendingRemoval.msi_session_name}?` : 'Remove session?'
        }
        heading="This deletes its metadata and annotations."
        body="This action cannot be undone."
      />
      <ConfirmDialog
        open={pendingSessionChange !== null}
        onClose={() => setPendingSessionChange(null)}
        onConfirm={() => {
          if (pendingSessionChange) updateRow(pendingSessionChange.key, pendingSessionChange);
          setPendingSessionChange(null);
        }}
        intent="warning"
        title={changingFrom ? `Change session ${changingFrom}?` : 'Change session?'}
        heading="This deletes its metadata and annotations."
        body="The current session's metadata and annotations will not carry over to the new one."
      />
      <Box sx={{ minWidth: 0 }}>
        <Box
          sx={{
            pb: 1.5,
            mb: 2,
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'nowrap',
              gap: 2,
              mb: 1,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5, minWidth: 0 }}>
              <Typography
                variant="overline"
                sx={{ fontWeight: 700, letterSpacing: 1.2, color: 'text.secondary', lineHeight: 1.2, flexShrink: 0 }}
              >
                Imaging sessions
              </Typography>
              <Typography variant="body2" color="text.secondary" noWrap>
                {headerStats}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, flexShrink: 0 }}>
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
                  '& .MuiToggleButtonGroup-grouped': {
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: '6px !important',
                    textTransform: 'none',
                    fontWeight: 600,
                    fontSize: '0.8125rem',
                    color: 'text.secondary',
                    bgcolor: 'background.paper',
                    '&:not(:first-of-type)': { ml: 0 },
                    '&:hover': { bgcolor: 'grey.50' },
                    '&.Mui-selected': {
                      bgcolor: 'primary.main',
                      color: 'primary.contrastText',
                      borderColor: 'primary.main',
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

          <Typography variant="body2" color="text.secondary" sx={{ mb: 0 }}>
            {modeHelp(subsetMode, excluded)}
          </Typography>
        </Box>

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
            sessionOptions={sessionOptions.filter(
              (name) => name === row.msi_session_name || !rows.some((r) => r.msi_session_name === name)
            )}
            subsetMode={subsetMode}
            readOnly={readOnly}
            onChange={(next) => updateRow(row.key, next)}
            onRemove={() => removeRow(row)}
            onRequestSessionChange={setPendingSessionChange}
            onUploadSubset={(file) => onUploadSubset(row, file)}
            onCount={reportCount}
            onAnnotated={reportAnnotated}
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

      <Box sx={{ display: { xs: 'none', md: 'block' }, alignSelf: 'stretch' }}>
        <DepositionSummary rows={rowsWithCounts} subsetMode={subsetMode} />
      </Box>
    </Box>
  );
}
