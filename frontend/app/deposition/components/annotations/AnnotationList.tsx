'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import SearchIcon from '@mui/icons-material/Search';
import { Box, Checkbox, InputAdornment, Link, TextField, Typography } from '@mui/material';
import { VariableSizeList, type ListChildComponentProps } from 'react-window';

import type { CopickKind, DepositionAnnotation } from '../../types';
import { annotationNeedsMetadata } from './scan';

const KIND_LABEL: Record<CopickKind, string> = {
  picks: 'Picks',
  segmentations: 'Segmentations',
  meshes: 'Meshes',
};
const KIND_ORDER: CopickKind[] = ['picks', 'segmentations', 'meshes'];
const HEADER_H = 34;
const ITEM_H = 56;
const LIST_H = 460;

export const annId = (a: DepositionAnnotation) => `${a.copick_kind}::${a.copick_ref}`;

function status(a: DepositionAnnotation): { label: string; color: string } {
  if (!a.is_selected) return { label: 'Not selected', color: 'text.disabled' };
  if (annotationNeedsMetadata(a)) return { label: 'Needs metadata', color: 'warning.main' };
  return { label: 'Ready to deposit', color: 'success.main' };
}

type Row = { type: 'header'; kind: CopickKind; count: number } | { type: 'item'; ann: DepositionAnnotation };

export function AnnotationList({
  annotations,
  activeId,
  onActivate,
  onToggle,
  onSetAll,
  readOnly = false,
}: {
  annotations: DepositionAnnotation[];
  activeId: string | null;
  onActivate: (id: string) => void;
  onToggle: (id: string, selected: boolean) => void;
  onSetAll: (selected: boolean) => void;
  readOnly?: boolean;
}) {
  const [filter, setFilter] = useState('');
  const q = filter.trim().toLowerCase();

  const visible = useMemo(
    () =>
      annotations.filter(
        (a) => !q || a.copick_ref.toLowerCase().includes(q) || (a.object_name ?? '').toLowerCase().includes(q)
      ),
    [annotations, q]
  );

  // Flatten grouped (header + items) into a single virtualized row list.
  const rows = useMemo<Row[]>(() => {
    const out: Row[] = [];
    for (const kind of KIND_ORDER) {
      const items = visible.filter((a) => a.copick_kind === kind);
      if (items.length === 0) continue;
      out.push({ type: 'header', kind, count: items.length });
      for (const a of items) out.push({ type: 'item', ann: a });
    }
    return out;
  }, [visible]);

  // Row heights vary (header vs item) and their positions shift on filter — reset the size cache.
  const listRef = useRef<VariableSizeList>(null);
  useEffect(() => listRef.current?.resetAfterIndex(0), [rows]);

  // react-window needs a numeric width — "100%" renders blank in flex/grid.
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver((entries) => setWidth(entries[0].contentRect.width));
    ro.observe(el);
    setWidth(el.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);

  const selectedCount = annotations.filter((a) => a.is_selected).length;
  const needCount = annotations.filter(annotationNeedsMetadata).length;

  let emptyMessage: string | null = null;
  if (annotations.length === 0) emptyMessage = 'No annotations found in the selected copick configs.';
  else if (rows.length === 0) emptyMessage = `No matches for “${filter}”.`;

  const RowRenderer = ({ index, style }: ListChildComponentProps) => {
    const row = rows[index];
    if (row.type === 'header') {
      return (
        <Box style={style} sx={{ display: 'flex', alignItems: 'flex-end', pb: 0.5 }}>
          <Typography variant="overline" sx={{ fontWeight: 700, color: 'text.secondary' }}>
            {KIND_LABEL[row.kind]}{' '}
            <Box component="span" sx={{ color: 'text.disabled' }}>
              {row.count} found
            </Box>
          </Typography>
        </Box>
      );
    }
    const a = row.ann;
    const id = annId(a);
    const st = status(a);
    const activeRow = id === activeId;
    return (
      <Box
        style={style}
        onClick={() => onActivate(id)}
        sx={{
          display: 'flex',
          gap: 1,
          alignItems: 'center',
          px: 1,
          cursor: 'pointer',
          borderRadius: 1,
          bgcolor: activeRow ? 'action.selected' : 'transparent',
          borderLeft: '3px solid',
          borderColor: activeRow ? 'primary.main' : 'transparent',
          '&:hover': { bgcolor: activeRow ? 'action.selected' : 'action.hover' },
        }}
      >
        <Checkbox
          size="small"
          checked={!!a.is_selected}
          disabled={readOnly}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => onToggle(id, e.target.checked)}
          sx={{ p: 0.25 }}
        />
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace' }} noWrap>
            {a.copick_ref}
          </Typography>
          <Typography variant="caption" sx={{ color: st.color, display: 'block' }}>
            {st.label}
          </Typography>
        </Box>
      </Box>
    );
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <TextField
        size="small"
        placeholder="Filter by reference or object"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        }}
        sx={{ mb: 1.5 }}
      />

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {selectedCount} of {annotations.length} selected
          {needCount > 0 && (
            <Box component="span" sx={{ color: 'warning.main' }}>
              {` · ${needCount} need metadata`}
            </Box>
          )}
        </Typography>
        {!readOnly && (
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Link component="button" type="button" variant="body2" underline="hover" onClick={() => onSetAll(true)}>
              All
            </Link>
            <Link
              component="button"
              type="button"
              variant="body2"
              underline="hover"
              color="text.secondary"
              onClick={() => onSetAll(false)}
            >
              None
            </Link>
          </Box>
        )}
      </Box>

      <Box ref={wrapRef} sx={{ width: '100%' }}>
        {emptyMessage ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
            {emptyMessage}
          </Typography>
        ) : (
          width > 0 && (
            <VariableSizeList
              ref={listRef}
              height={LIST_H}
              width={width}
              itemCount={rows.length}
              itemSize={(i) => (rows[i].type === 'header' ? HEADER_H : ITEM_H)}
              overscanCount={8}
            >
              {RowRenderer}
            </VariableSizeList>
          )
        )}
      </Box>
    </Box>
  );
}
