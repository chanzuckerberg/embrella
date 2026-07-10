'use client';

import { Fragment, useMemo, useState } from 'react';
import { Button } from '@czi-sds/components';
import {
  Box,
  CircularProgress,
  Container,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material';

import { useSubmissions } from '../hooks/useSubmissions';
import type { Deposition } from '../types';
import { COLS, FILTERS, type FilterKey } from './constants';
import { AddDatasetDialog } from './components/AddDatasetDialog';
import { ColGroup } from './components/ColGroup';
import { DatasetRow } from './components/DatasetRow';
import { GroupHeaderRow } from './components/GroupHeaderRow';
import { NewSubmissionDialog } from './components/NewSubmissionDialog';

export default function SubmissionsPage() {
  const [newOpen, setNewOpen] = useState(false);
  const [addDatasetFor, setAddDatasetFor] = useState<Deposition | null>(null);
  const [filter, setFilter] = useState<FilterKey>('all');
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

  const { data, isPending, isError } = useSubmissions('mine');
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
    const all = submissions ?? [];
    if (filter === 'all') return all;
    return all
      .map((dep) => ({ ...dep, datasets: (dep.datasets ?? []).filter((ds) => ds.status === filter) }))
      .filter((dep) => (dep.datasets ?? []).length > 0);
  }, [submissions, filter]);

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
              // macOS hides overlay scrollbars until you scroll, so users don't realizethe table is scrollable 
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
                    <TableCell key={c.key} align={c.align} sx={{ fontWeight: 700 }}>
                      {c.label}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COLS.length} sx={{ color: 'text.secondary', textAlign: 'center', py: 4 }}>
                      No depositions match this filter.
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
                      {open && datasets.map((ds) => <DatasetRow key={ds.id} dataset={ds} />)}
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
        <Typography  color="text.secondary" sx={{ mt: 2 }}>
          Showing {visible.length} of {submissions.length} depositions
        </Typography>
      </>
    );
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          My Submissions
        </Typography>
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
            label={`${f.label} ${counts[f.key]}`}
            sx={{ minHeight: 40, textTransform: 'none' }}
          />
        ))}
      </Tabs>

      {renderContent()}

      <NewSubmissionDialog open={newOpen} onClose={() => setNewOpen(false)} />
      <AddDatasetDialog deposition={addDatasetFor} onClose={() => setAddDatasetFor(null)} />
    </Container>
  );
}
