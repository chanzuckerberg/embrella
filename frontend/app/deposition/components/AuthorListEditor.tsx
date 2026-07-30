'use client';

import { forwardRef, Fragment, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Icon } from '@czi-sds/components';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import {
  Avatar,
  Box,
  Checkbox,
  Chip,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Link,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

import type { AuthorRef, Person } from '../types';
import { usePeopleByIds } from '../hooks/usePeopleByIds';
import { updatePerson } from '../services/depositionApi';
import { ORCID_RE, orcidChecksumOk } from '../services/identifiers';
import { AddAuthorDialog } from '../depositions/AddAuthorDialog';
import { IdentifierField } from './IdentifierField';

const AVATAR_COLORS = ['#6C5CE7', '#00B894', '#0984E3', '#E17055', '#E84393', '#00CEC9'];

const personName = (p?: Person) => (p ? `${p.given_name} ${p.family_name}`.trim() : 'Unknown author');

const initials = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('') || '?';

const splitFullName = (full: string) => {
  const parts = full.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { given_name: '', family_name: '' };
  if (parts.length === 1) return { given_name: parts[0], family_name: '' };
  return { given_name: parts[0], family_name: parts.slice(1).join(' ') };
};

const cellSx = {
  py: 1.25,
  px: 1.5,
  borderColor: 'divider',
  fontSize: '0.8125rem',
  overflow: 'hidden',
  verticalAlign: 'middle',
  lineHeight: 1.4,
};

const headCellSx = {
  ...cellSx,
  py: 1,
  fontWeight: 700,
  fontSize: '0.6875rem',
  letterSpacing: 0.6,
  color: 'text.secondary',
  bgcolor: 'grey.50',
};

const ellipsisSx = {
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

/** Compact P/C badge used in the table name column + footer legend. */
function RoleChip({ kind }: { kind: 'P' | 'C' }) {
  const primary = kind === 'P';
  return (
    <Box
      component="span"
      aria-label={primary ? 'Primary' : 'Corresponding'}
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 18,
        height: 18,
        flexShrink: 0,
        borderRadius: '4px',
        fontWeight: 700,
        fontSize: 11,
        lineHeight: 1,
        bgcolor: (t) => `${primary ? t.palette.primary.main : t.palette.success.main}24`,
        color: primary ? 'primary.main' : 'success.dark',
      }}
    >
      {kind}
    </Box>
  );
}

/** Full-word role pill used in the expanded edit card header. */
function RolePill({ kind }: { kind: 'primary' | 'corresponding' }) {
  const primary = kind === 'primary';
  return (
    <Chip
      label={primary ? 'Primary' : 'Corresponding'}
      size="small"
      sx={{
        height: 22,
        fontWeight: 600,
        fontSize: 12,
        bgcolor: (t) => `${primary ? t.palette.primary.main : t.palette.success.main}24`,
        color: primary ? 'primary.main' : 'success.dark',
      }}
    />
  );
}

type AuthorEditPanelHandle = { save: () => Promise<void> };

// Expanded per-row editor. Identity (name/affiliation/orcid) edits the shared
// People.Person via updatePerson — directory-wide. Primary/Corresponding are
// per-list flags on the AuthorRef and toggle immediately.
const AuthorEditPanel = forwardRef<
  AuthorEditPanelHandle,
  {
    person?: Person;
    authorRef: AuthorRef;
    order: number;
    disabled: boolean;
    onToggle: (key: 'is_primary' | 'is_corresponding') => void;
    onRemove: () => void;
  }
>(function AuthorEditPanel({ person, authorRef, order, disabled, onToggle, onRemove }, ref) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState(personName(person) === 'Unknown author' ? '' : personName(person));
  const [orcid, setOrcid] = useState(person?.orcid ?? '');
  const [affiliation, setAffiliation] = useState(person?.affiliation ?? '');

  const orcidTrimmed = orcid.trim();
  const orcidOk = orcidTrimmed === '' || (ORCID_RE.test(orcidTrimmed) && orcidChecksumOk(orcidTrimmed));
  const { given_name, family_name } = splitFullName(fullName);

  const dirty =
    !!person &&
    (given_name !== (person.given_name ?? '') ||
      family_name !== (person.family_name ?? '') ||
      orcidTrimmed !== (person.orcid ?? '') ||
      affiliation.trim() !== (person.affiliation ?? ''));

  const saveMutation = useMutation({
    mutationFn: () =>
      updatePerson(authorRef.author_id, {
        given_name: given_name.trim(),
        family_name: family_name.trim(),
        orcid: orcidTrimmed || null,
        affiliation: affiliation.trim() || null,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['people', 'by-ids'] }),
  });

  useImperativeHandle(
    ref,
    () => ({
      save: async () => {
        if (!disabled && dirty && orcidOk) await saveMutation.mutateAsync();
      },
    }),
    [disabled, dirty, orcidOk, saveMutation]
  );

  const name = personName(person);

  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        p: 2.5,
        pb: 3,
        bgcolor: 'grey.50',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
          <Avatar
            sx={{ width: 24, height: 24, fontSize: 11, bgcolor: AVATAR_COLORS[(order - 1) % AVATAR_COLORS.length] }}
          >
            {initials(name)}
          </Avatar>
          <Typography
            variant="body2"
            sx={{ fontWeight: 700, color: 'text.secondary', letterSpacing: 0.6, fontSize: '0.75rem' }}
          >
            AUTHOR {order}
          </Typography>
          {authorRef.is_primary && <RolePill kind="primary" />}
          {authorRef.is_corresponding && <RolePill kind="corresponding" />}
        </Box>
        {!disabled && (
          <IconButton size="small" aria-label={`Remove author ${order}`} onClick={onRemove}>
            <Icon sdsIcon="TrashCan" sdsSize="s" color="gray" />
          </IconButton>
        )}
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 2,
          mb: 2,
          mt: 5,
        }}
      >
        <TextField
          label="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          size="small"
          fullWidth
          disabled={disabled}
        />
        <TextField
          label="Affiliation"
          value={affiliation}
          onChange={(e) => setAffiliation(e.target.value)}
          size="small"
          fullWidth
          disabled={disabled}
        />
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: { xs: 'stretch', sm: 'center' },
          gap: { xs: 1.5, sm: 2.5 },
        }}
      >
        <IdentifierField
          kind="orcid"
          label="ORCID iD"
          value={orcid}
          onChange={setOrcid}
          placeholder="0000-0000-0000-0000"
          size="small"
          disabled={disabled}
          inputProps={{ 'aria-label': 'ORCID iD' }}
          sx={{ width: { xs: '100%', sm: 260 }, mt: 3, flexShrink: 0 }}
        />
        <FormControlLabel
          control={
            <Checkbox
              size="small"
              checked={authorRef.is_primary}
              onChange={() => onToggle('is_primary')}
              disabled={disabled}
            />
          }
          label="Primary author"
          sx={{ mr: 0, ml: 0, my: 0, mt: -2, flexShrink: 0 }}
        />
        <FormControlLabel
          control={
            <Checkbox
              size="small"
              checked={authorRef.is_corresponding}
              onChange={() => onToggle('is_corresponding')}
              disabled={disabled}
            />
          }
          label="Corresponding author"
          sx={{ mr: 0, ml: 0, my: 0, mt: -2, flexShrink: 0 }}
        />
      </Box>
    </Box>
  );
});

export function AuthorListEditor({
  authors,
  onChange,
  disabled = false,
}: {
  authors: AuthorRef[];
  onChange: (authors: AuthorRef[]) => void;
  disabled?: boolean;
}) {
  const [addOpen, setAddOpen] = useState(false);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const editPanelRef = useRef<AuthorEditPanelHandle | null>(null);
  const [search, setSearch] = useState('');
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);

  const { data: resolved } = usePeopleByIds(authors.map((a) => a.author_id));

  const renumber = (list: AuthorRef[]) => list.map((a, i) => ({ ...a, author_list_order: i }));
  const toggle = (i: number, key: 'is_primary' | 'is_corresponding') =>
    onChange(authors.map((a, idx) => (idx === i ? { ...a, [key]: !a[key] } : a)));
  const remove = (i: number) => {
    onChange(renumber(authors.filter((_, idx) => idx !== i)));
    setEditingIdx(null);
  };
  const add = (personId: number) =>
    onChange(
      renumber([
        ...authors,
        { author_id: personId, is_primary: false, is_corresponding: false, author_list_order: authors.length },
      ])
    );

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

  // Reorder operates on the full list; disable drag while a search filter is active
  // so drag indices can't drift from the underlying array.
  const filtering = search.trim() !== '';
  const canReorder = !disabled && !filtering;

  const byId = useMemo(() => new Map((resolved ?? []).map((p) => [p.id, p])), [resolved]);
  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return authors
      .map((a, idx) => ({ a, idx, p: byId.get(a.author_id) }))
      .filter(
        ({ p }) =>
          !q ||
          personName(p).toLowerCase().includes(q) ||
          p?.orcid?.toLowerCase().includes(q) ||
          p?.affiliation?.toLowerCase().includes(q)
      );
  }, [authors, byId, search]);

  return (
    <Box sx={{ minWidth: 0 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1.5,
          mb: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.3 }}>
            Author list
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {authors.length} {authors.length === 1 ? 'author' : 'authors'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: '1 1 auto', justifyContent: 'flex-end' }}>
          <TextField
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name or affiliation"
            size="small"
            disabled={disabled}
            sx={{ width: { xs: '100%', sm: 240 }, maxWidth: 280 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Icon sdsIcon="Search" sdsSize="s" color="gray" />
                </InputAdornment>
              ),
            }}
          />
          <Button sdsType="secondary" sdsStyle="outline" disabled={disabled} onClick={() => setAddOpen(true)}>
            + Add author
          </Button>
        </Box>
      </Box>

      <AddAuthorDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        existingIds={authors.map((a) => a.author_id)}
        onAdd={add}
      />

      {authors.length === 0 ? (
        <Box
          sx={{
            border: '1px dashed',
            borderColor: 'divider',
            borderRadius: 2,
            py: 6,
            px: 3,
            textAlign: 'center',
          }}
        >
          <Typography sx={{ fontWeight: 700, mb: 0.5 }}>No authors added yet</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Add an author from the People directory.
          </Typography>
          <Button sdsType="primary" sdsStyle="solid" disabled={disabled} onClick={() => setAddOpen(true)}>
            + Add author
          </Button>
        </Box>
      ) : (
        <Box
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 2,
            overflow: 'auto',
            minWidth: 0,
          }}
        >
          <Table size="small" sx={{ tableLayout: 'fixed', width: '100%', minWidth: 680 }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ ...headCellSx, width: 64 }}>ORDER</TableCell>
                <TableCell sx={{ ...headCellSx, width: '34%' }}>NAME</TableCell>
                <TableCell sx={{ ...headCellSx, width: '20%' }}>AFFILIATION</TableCell>
                <TableCell sx={{ ...headCellSx, width: 168 }}>ORCID</TableCell>
                <TableCell align="right" sx={{ ...headCellSx, width: 96 }}>
                  ACTIONS
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {visible.map(({ a, idx, p }) => {
                const isEditing = editingIdx === idx;
                const isDropTarget = dragIdx !== null && dragIdx !== idx && overIdx === idx;
                const name = personName(p);
                return (
                  <Fragment key={a.author_id}>
                    <TableRow
                      onDragOver={(e) => {
                        if (dragIdx === null) return;
                        e.preventDefault();
                        setOverIdx(idx);
                      }}
                      onDrop={() => handleDrop(idx)}
                      sx={{
                        opacity: dragIdx === idx ? 0.4 : 1,
                        ...(isDropTarget ? { boxShadow: (t) => `inset 0 2px 0 0 ${t.palette.primary.main}` } : {}),
                        '& > td': { borderBottom: isEditing ? 'none' : '1px solid', borderColor: 'divider' },
                      }}
                    >
                      <TableCell sx={cellSx}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                          {canReorder && (
                            <Box
                              draggable
                              onDragStart={() => setDragIdx(idx)}
                              onDragEnd={() => {
                                setDragIdx(null);
                                setOverIdx(null);
                              }}
                              aria-label="Drag to reorder"
                              sx={{
                                display: 'inline-flex',
                                color: 'text.disabled',
                                cursor: 'grab',
                                '&:active': { cursor: 'grabbing' },
                              }}
                            >
                              <DragIndicatorIcon fontSize="small" />
                            </Box>
                          )}
                          <Typography variant="body2" color="text.secondary">
                            {idx + 1}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell sx={cellSx}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0 }}>
                          <Avatar
                            sx={{
                              width: 24,
                              height: 24,
                              fontSize: 11,
                              flexShrink: 0,
                              bgcolor: AVATAR_COLORS[idx % AVATAR_COLORS.length],
                            }}
                          >
                            {initials(name)}
                          </Avatar>
                          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
                            <Typography variant="body2" title={name} sx={{ fontWeight: 600, ...ellipsisSx }}>
                              {name}
                            </Typography>
                            {(a.is_primary || a.is_corresponding) && (
                              <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, flexShrink: 0 }}>
                                {a.is_primary && <RoleChip kind="P" />}
                                {a.is_corresponding && <RoleChip kind="C" />}
                              </Box>
                            )}
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell sx={{ ...cellSx, color: p?.affiliation ? 'text.primary' : 'text.disabled' }}>
                        {p?.affiliation ? (
                          <Tooltip title={p.affiliation} enterDelay={400}>
                            <Typography component="span" variant="body2" sx={ellipsisSx}>
                              {p.affiliation}
                            </Typography>
                          </Tooltip>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell sx={{ ...cellSx, color: p?.orcid ? 'text.primary' : 'text.disabled' }}>
                        {p?.orcid ? (
                          <Tooltip title={p.orcid} enterDelay={300}>
                            <Typography
                              component="span"
                              variant="body2"
                              sx={{
                                ...ellipsisSx,
                                display: 'block',
                                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                                fontSize: '0.75rem',
                                letterSpacing: 0,
                                cursor: 'default',
                              }}
                            >
                              {p.orcid}
                            </Typography>
                          </Tooltip>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                      <TableCell align="right" sx={{ ...cellSx, overflow: 'visible' }}>
                        <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75, whiteSpace: 'nowrap' }}>
                          <Link
                            component="button"
                            type="button"
                            variant="body2"
                            underline="hover"
                            sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}
                            onClick={async () => {
                              if (isEditing) {
                                await editPanelRef.current?.save();
                                setEditingIdx(null);
                              } else {
                                setEditingIdx(idx);
                              }
                            }}
                          >
                            {isEditing ? 'Done' : 'Edit'}
                          </Link>
                          {!disabled && (
                            <IconButton
                              size="small"
                              aria-label={`Remove author ${idx + 1}`}
                              onClick={() => remove(idx)}
                            >
                              <Icon sdsIcon="TrashCan" sdsSize="s" color="gray" />
                            </IconButton>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>

                    {isEditing && (
                      <TableRow>
                        <TableCell colSpan={5} sx={{ py: 2, px: 2, bgcolor: 'common.white', borderColor: 'divider' }}>
                          <AuthorEditPanel
                            key={p?.id ?? 'loading'}
                            ref={editPanelRef}
                            person={p}
                            authorRef={a}
                            order={idx + 1}
                            disabled={disabled}
                            onToggle={(key) => toggle(idx, key)}
                            onRemove={() => remove(idx)}
                          />
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      )}

      {authors.length > 0 && (
        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2, mt: 1.75 }}>
          <Typography variant="caption" color="text.secondary">
            {filtering ? `Showing ${visible.length} of ${authors.length}` : `Showing all ${authors.length}`}
          </Typography>
          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75 }}>
            <RoleChip kind="P" />
            <Typography variant="caption" color="text.secondary">
              Primary
            </Typography>
          </Box>
          <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75 }}>
            <RoleChip kind="C" />
            <Typography variant="caption" color="text.secondary">
              Corresponding
            </Typography>
          </Box>
          {filtering && authors.length > 1 && (
            <Typography variant="caption" color="text.secondary">
              · Clear search to reorder
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
}
