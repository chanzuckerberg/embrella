'use client';

import { useState } from 'react';
import { Button } from '@czi-sds/components';
import CloseIcon from '@mui/icons-material/Close';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Box, IconButton, Radio, Table, TableBody, TableCell, TableHead, TableRow, Tooltip, Typography } from '@mui/material';

import type { AuthorRef, Person } from '../types';
import { usePeopleByIds } from '../hooks/usePeopleByIds';
import { AddAuthorDialog } from './AddAuthorDialog';

const personName = (p?: Person) => (p ? `${p.given_name} ${p.family_name}`.trim() : 'Unknown author');

const AUTHORS_HELP =
  'Drag to reorder. One Primary and one Corresponding author (can be the same); click again to clear.';

export function AuthorTable({
  authors,
  onChange,
  disabled = false,
}: {
  authors: AuthorRef[];
  onChange: (authors: AuthorRef[]) => void;
  disabled?: boolean;
}) {
  const [addOpen, setAddOpen] = useState(false);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);
  const { data: resolved } = usePeopleByIds(authors.map((a) => a.author_id));
  const byId = new Map((resolved ?? []).map((p) => [p.id, p]));

  const renumber = (list: AuthorRef[]) => list.map((a, i) => ({ ...a, author_list_order: i }));

  const toggleFlag = (idx: number, key: 'is_primary' | 'is_corresponding') => {
    const wasOn = authors[idx][key];
    onChange(authors.map((a, i) => ({ ...a, [key]: wasOn ? false : i === idx })));
  };

  const remove = (idx: number) => onChange(renumber(authors.filter((_, i) => i !== idx)));

  const reorder = (from: number, to: number) => {
    if (from === to) return;
    const next = [...authors];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    onChange(renumber(next));
  };

  const handleDrop = (to: number) => {
    if (dragIdx !== null) reorder(dragIdx, to);
    setDragIdx(null);
    setOverIdx(null);
  };

  const add = (personId: number) =>
    onChange(
      renumber([
        ...authors,
        { author_id: personId, is_primary: false, is_corresponding: false, author_list_order: authors.length },
      ]),
    );

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Authors
          </Typography>
          {authors.length > 0 && (
            <Tooltip title={AUTHORS_HELP} placement="top" arrow>
              <InfoOutlinedIcon
                fontSize="small"
                aria-label="How authors work"
                sx={{ color: 'text.secondary', cursor: 'help' }}
              />
            </Tooltip>
          )}
        </Box>
        <Button sdsType="primary" sdsStyle="minimal" disabled={disabled} onClick={() => setAddOpen(true)}>
          + Add author
        </Button>
      </Box>

      <AddAuthorDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        existingIds={authors.map((a) => a.author_id)}
        onAdd={add}
      />

      {authors.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No authors yet.
        </Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 48 }} />
              <TableCell sx={{ fontWeight: 700 }}>Name</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>ORCID</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>Email</TableCell>
              <TableCell align="center" sx={{ fontWeight: 700 }}>
                Primary
              </TableCell>
              <TableCell align="center" sx={{ fontWeight: 700 }}>
                Corresp.
              </TableCell>
              <TableCell sx={{ width: 40 }} />
            </TableRow>
          </TableHead>
          <TableBody>
            {authors.map((a, idx) => {
              const p = byId.get(a.author_id);
              const isDropTarget = dragIdx !== null && dragIdx !== idx && overIdx === idx;
              return (
                <TableRow
                  key={a.author_id}
                  onDragOver={(e) => {
                    if (dragIdx === null) return;
                    e.preventDefault();
                    setOverIdx(idx);
                  }}
                  onDrop={() => handleDrop(idx)}
                  sx={{
                    opacity: dragIdx === idx ? 0.4 : 1,
                    ...(isDropTarget
                      ? { boxShadow: (theme) => `inset 0 2px 0 0 ${theme.palette.primary.main}` }
                      : {}),
                  }}
                >
                  <TableCell sx={{ px: 0.5 }}>
                    <Box
                      draggable={!disabled}
                      onDragStart={() => setDragIdx(idx)}
                      onDragEnd={() => {
                        setDragIdx(null);
                        setOverIdx(null);
                      }}
                      aria-label="Drag to reorder"
                      sx={{
                        display: 'inline-flex',
                        color: 'text.disabled',
                        cursor: disabled ? 'default' : 'grab',
                        '&:active': { cursor: disabled ? 'default' : 'grabbing' },
                      }}
                    >
                      <DragIndicatorIcon fontSize="small" />
                    </Box>
                  </TableCell>
                  <TableCell>{personName(p)}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>{p?.orcid ?? '—'}</TableCell>
                  <TableCell>{p?.contact_email ?? '—'}</TableCell>
                  <TableCell align="center">
                    <Radio
                      size="small"
                      checked={a.is_primary}
                      disabled={disabled}
                      onClick={() => toggleFlag(idx, 'is_primary')}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Radio
                      size="small"
                      checked={a.is_corresponding}
                      disabled={disabled}
                      onClick={() => toggleFlag(idx, 'is_corresponding')}
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" aria-label="Remove author" disabled={disabled} onClick={() => remove(idx)}>
                      <CloseIcon fontSize="small" sx={{ color: 'error.main' }} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </Box>
  );
}
