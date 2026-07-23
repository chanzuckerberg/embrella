'use client';

import { Fragment, useMemo, useState } from 'react';
import { Button } from '@czi-sds/components';
import SearchIcon from '@mui/icons-material/Search';
import {
  Box,
  Checkbox,
  CircularProgress,
  Container,
  FormControl,
  FormControlLabel,
  InputAdornment,
  MenuItem,
  Paper,
  Select,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';

import { useSubmissions } from '../hooks/useSubmissions';
import type { Deposition } from '../types';
import { COLS, FILTERS, SORT_OPTIONS, type FilterKey, type SortKey } from './constants';
import { compareDatasets, datasetMatches, depositionMatches } from './utils';
import { ColGroup } from './components/ColGroup';
import { DatasetRow } from './components/DatasetRow';
import { GroupHeaderRow } from './components/GroupHeaderRow';
import { ReservationModal } from './components/ReservationModal';

export default function SubmissionsPage() {
  const [newOpen, setNewOpen] = useState(false);
  const [addDatasetFor, setAddDatasetFor] = useState<Deposition | null>(null);
  const [filter, setFilter] = useState<FilterKey>('all');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortKey>('recent');
  const [scope, setScope] = useState<'all' | 'mine'>('all');
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

  const { data, isPending, isError } = useSubmissions(scope === 'mine' ? 'mine' : undefined);
  const submissions = data?.submissions ?? null;

  const toggle = (id: number) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  // Per-status counts across all datasets (for the filter tabs).
  const counts = useMemo(() => {
    const c: Record<FilterKey, number> = { all: 0, draft: 0, syncing: 0, pushed: 0, failed: 0 };
    (submissions ?? []).forEach((dep) =>
      (dep.datasets ?? []).forEach((ds) => {
        c.all += 1;
        c[ds.status] += 1;
      }),
    );
    return c;
  }, [submissions]);

  // Depositions whose datasets match the active filter.
  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    const groups = (submissions ?? [])
      .map((dep) => {
        const depHit = q !== '' && depositionMatches(dep, q);
        let datasets = (dep.datasets ?? []).filter((ds) => filter === 'all' || ds.status === filter);
        if (q !== '' && !depHit) datasets = datasets.filter((ds) => datasetMatches(ds, q));
        datasets = [...datasets].sort((a, b) => compareDatasets(a, b, sort));
        return { ...dep, datasets };
      })
      .filter((dep) => dep.datasets.length > 0);
    // Order the groups by their representative dataset.
    return groups.sort((a, b) => compareDatasets(a.datasets[0], b.datasets[0], sort));
  }, [submissions, filter, search, sort]);

  const visibleDatasetCount = useMemo(
    () => visible.reduce((n, dep) => n + dep.datasets.length, 0),
    [visible],
  );

  const renderContent = () => {
    if (isError) {
      return <Typography color="error">Failed to load submissions. Please try again.</Typography>;
    }
    if (isPending || submissions === null) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      );
    }
    if (submissions.length === 0) {
      return (
        <Box sx={{ color: 'text.secondary', py: 6, textAlign: 'center' }}>
          <Typography>No submissions yet.</Typography>
          <Typography variant="body2">Use “+ New Submission” to reserve a deposition and get started.</Typography>
        </Box>
      );
    }
    return (
      <>
        <Paper variant="outlined">
          <TableContainer
            sx={{
              overflowX: 'auto',
              // Keep a visible horizontal scrollbar (macOS overlay scrollbars are easy to miss).
              '&::-webkit-scrollbar': { height: 8, WebkitAppearance: 'none' },
              '&::-webkit-scrollbar-thumb': { borderRadius: 4, backgroundColor: 'rgba(0, 0, 0, 0.35)' },
              '&::-webkit-scrollbar-track': { backgroundColor: 'rgba(0, 0, 0, 0.06)' },
              scrollbarWidth: 'thin', // Firefox
            }}
          >
            <Table size="small" sx={{ tableLayout: 'fixed', minWidth: 720 }}>
              <ColGroup />
              <TableHead>
                <TableRow>
                  {COLS.map((c) => (
                    <TableCell
                      key={c.key}
                      align={c.align}
                      sx={{
                        fontWeight: 600,
                        fontSize: 12,
                        letterSpacing: 0.6,
                        textTransform: 'uppercase',
                        color: 'text.secondary',
                      }}
                    >
                      {c.label}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COLS.length} sx={{ color: 'text.secondary', textAlign: 'center', py: 4 }}>
                      No datasets match your search or filter.
                    </TableCell>
                  </TableRow>
                )}
                {visible.map((dep) => {
                  const open = !collapsed.has(dep.id);
                  const datasets = dep.datasets ?? [];
                  return (
                    <Fragment key={dep.id}>
                      <GroupHeaderRow
                        deposition={dep}
                        open={open}
                        onToggle={() => toggle(dep.id)}
                        onAddDataset={() => setAddDatasetFor(dep)}
                      />
                      {open && datasets.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={COLS.length} sx={{ color: 'text.secondary' }}>
                            No datasets yet.
                          </TableCell>
                        </TableRow>
                      )}
                      {open && datasets.map((ds) => <DatasetRow key={ds.id} dataset={ds} isOwner={dep.is_owner} />)}
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Showing {visibleDatasetCount} {visibleDatasetCount === 1 ? 'dataset' : 'datasets'} across {visible.length}{' '}
          {visible.length === 1 ? 'deposition' : 'depositions'}
        </Typography>
      </>
    );
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Submissions
          </Typography>
          <Typography color="text.secondary">
            {counts.all} {counts.all === 1 ? 'dataset' : 'datasets'} across {submissions?.length ?? 0}{' '}
            {(submissions?.length ?? 0) === 1 ? 'deposition' : 'depositions'}
          </Typography>
        </Box>
        <Button sdsType="primary" sdsStyle="solid" onClick={() => setNewOpen(true)}>
          + New Submission
        </Button>
      </Box>

      <Tabs
        value={filter}
        onChange={(_, v: FilterKey) => setFilter(v)}
        sx={{ mb: 2, borderBottom: 1, borderColor: 'divider', minHeight: 40 }}
      >
        {FILTERS.map((f) => (
          <Tab
            key={f.key}
            value={f.key}
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                {f.label}
                <Box
                  component="span"
                  sx={{
                    minWidth: 20,
                    px: 0.75,
                    borderRadius: 5,
                    fontSize: 12,
                    fontWeight: 600,
                    lineHeight: '18px',
                    textAlign: 'center',
                    bgcolor: filter === f.key ? 'primary.main' : 'action.selected',
                    color: filter === f.key ? 'primary.contrastText' : 'text.secondary',
                  }}
                >
                  {counts[f.key]}
                </Box>
              </Box>
            }
            sx={{ minHeight: 40, textTransform: 'none' }}
          />
        ))}
      </Tabs>

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={scope === 'mine'}
                onChange={(e) => setScope(e.target.checked ? 'mine' : 'all')}
              />
            }
            label="Only Mine"
            sx={{ whiteSpace: 'nowrap', mr: 0 }}
          />
          <TextField
            size="small"
            placeholder="Search datasets or depositions"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ flex: 1, maxWidth: 400 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
        </Box>
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <Select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            renderValue={(v) => `Sort: ${SORT_OPTIONS.find((o) => o.key === v)?.label ?? ''}`}
          >
            {SORT_OPTIONS.map((o) => (
              <MenuItem key={o.key} value={o.key}>
                {o.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {renderContent()}

      {newOpen && <ReservationModal open onClose={() => setNewOpen(false)} />}
      {addDatasetFor && (
        <ReservationModal
          open
          onClose={() => setAddDatasetFor(null)}
          initialMode="existing_deposition"
          lockedDeposition={addDatasetFor}
        />
      )}
    </Container>
  );
}
