'use client';

import { useEffect, useRef, useState } from 'react';
import { Chip, TextField, Box, Popper, Paper, Typography, ClickAwayListener } from '@mui/material';
import { API, DJANGO_URL, POST_API } from '@app/common/constants/api';

export interface LabelData {
  id: number;
  name: string;
  color: string;
}

interface LabelChipProps {
  gridId: number;
  labels: LabelData[];
  /**
   * When provided, the chip is fully controlled: `controlledLabels` is the
   * source of truth for what's rendered, and `onSave` is invoked instead of
   * the default PATCH whenever the label set changes. Use this when multiple
   * editors on the same row share label state (see Screening tab).
   */
  controlledLabels?: LabelData[];
  onSave?: (next: LabelData[]) => Promise<void> | void;
}

export const LabelChip = ({ gridId, labels: initialLabels, controlledLabels, onSave }: LabelChipProps) => {
  const isControlled = controlledLabels !== undefined;
  const [internalLabels, setInternalLabels] = useState<LabelData[]>(initialLabels);
  const labels = isControlled ? controlledLabels : internalLabels;

  const [editing, setEditing] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<LabelData[]>([]);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [allLabels, setAllLabels] = useState<LabelData[]>([]);

  const anchorRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Fetch all labels once when entering edit mode
  useEffect(() => {
    if (!editing) return;
    fetch(`${DJANGO_URL}${API.LABELS}`, { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => setAllLabels(Array.isArray(data) ? data : (data.results ?? [])))
      .catch(() => setAllLabels([]));
  }, [editing]);

  // Filter suggestions when input changes
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const selectedIds = new Set(labels.map((l) => l.id));
      const available = allLabels.filter((l) => !selectedIds.has(l.id));
      if (!inputValue.trim()) {
        setSuggestions(available.slice(0, 5));
        return;
      }
      const term = inputValue.toLowerCase();
      const filtered = available.filter((l) => l.name.toLowerCase().includes(term));
      setSuggestions(filtered);
    }, 150);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [inputValue, allLabels, labels]);

  useEffect(() => {
    setHighlightedIndex(-1);
  }, [suggestions]);

  const saveLabels = async (newLabels: LabelData[]) => {
    if (!isControlled) setInternalLabels(newLabels);
    if (onSave) {
      await onSave(newLabels);
      return;
    }
    const url = `${DJANGO_URL}${POST_API.UPDATE_GRID_LABELS.replace('grid_id', String(gridId))}`;
    try {
      const res = await fetch(url, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label_ids: newLabels.map((l) => l.id) }),
      });
      if (!res.ok) {
        console.error('Failed to update labels:', res.status, await res.text());
      }
    } catch (e) {
      console.error('Failed to update labels:', e);
    }
  };

  const addLabel = async (label: LabelData) => {
    if (labels.some((l) => l.id === label.id)) return;
    const updated = [...labels, label];
    await saveLabels(updated);
    setInputValue('');
    setSuggestions([]);
    inputRef.current?.focus();
  };

  const createAndAddLabel = async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;

    // Check if it already exists
    const existing = allLabels.find((l) => l.name.toLowerCase() === trimmed.toLowerCase());
    if (existing) {
      await addLabel(existing);
      return;
    }

    try {
      const res = await fetch(`${DJANGO_URL}${POST_API.CREATE_LABEL}`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!res.ok) {
        console.error('Failed to create label:', res.status, await res.text());
        return;
      }
      const label: LabelData = await res.json();
      setAllLabels((prev) => [...prev, label]);
      await addLabel(label);
    } catch (e) {
      console.error('Failed to create label:', e);
    }
  };

  const removeLabel = async (labelId: number) => {
    const updated = labels.filter((l) => l.id !== labelId);
    await saveLabels(updated);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
        addLabel(suggestions[highlightedIndex]);
      } else if (inputValue.trim()) {
        createAndAddLabel(inputValue);
      }
    } else if (e.key === 'Escape') {
      setEditing(false);
    } else if (e.key === 'Backspace' && inputValue === '' && labels.length > 0) {
      removeLabel(labels[labels.length - 1].id);
    }
  };

  const showSuggestions = editing && suggestions.length > 0;

  if (!editing) {
    return (
      <Box
        onClick={(e) => {
          e.stopPropagation();
          setEditing(true);
          setTimeout(() => inputRef.current?.focus(), 0);
        }}
        sx={{
          display: 'flex',
          gap: '3px',
          flexWrap: 'wrap',
          cursor: 'pointer',
          minHeight: 24,
          '&:hover': { opacity: 0.8 },
        }}
      >
        {labels.length > 0 ? (
          labels.map((label) => (
            <Chip
              key={label.id}
              label={label.name}
              size="small"
              sx={{
                backgroundColor: label.color,
                color: '#fff',
                fontWeight: 500,
                height: 20,
                fontSize: 12,
                borderRadius: '4px',
                '& .MuiChip-label': { px: '4px' },
              }}
            />
          ))
        ) : (
          <Chip
            label="+ Add"
            size="small"
            variant="outlined"
            sx={{ height: 20, fontSize: 12, borderRadius: '4px', '& .MuiChip-label': { px: '4px' } }}
          />
        )}
      </Box>
    );
  }

  return (
    <ClickAwayListener onClickAway={() => setEditing(false)}>
      <Box ref={anchorRef} onClick={(e) => e.stopPropagation()}>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '2px',
            border: '1px solid',
            borderColor: 'primary.main',
            borderRadius: 1,
            p: '4px',
            minHeight: 32,
            backgroundColor: '#fff',
          }}
        >
          {labels.map((label) => (
            <Chip
              key={label.id}
              label={label.name}
              size="small"
              onDelete={(e) => {
                e.stopPropagation();
                removeLabel(label.id);
              }}
              sx={{
                backgroundColor: label.color,
                color: '#fff',
                fontWeight: 500,
                height: 20,
                fontSize: 12,
                borderRadius: '4px',
                '& .MuiChip-label': { px: '4px' },
                '& .MuiChip-deleteIcon': {
                  color: 'rgba(255,255,255,0.7)',
                  fontSize: 14,
                  mr: '2px',
                  '&:hover': { color: '#fff' },
                },
              }}
            />
          ))}
          <TextField
            inputRef={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type label..."
            variant="standard"
            size="small"
            autoFocus
            InputProps={{ disableUnderline: true }}
            sx={{ flex: 1, minWidth: 80, '& input': { p: 0, fontSize: 12 } }}
          />
        </Box>

        <Popper
          open={showSuggestions}
          anchorEl={anchorRef.current}
          placement="bottom-start"
          style={{ zIndex: 1300, width: anchorRef.current?.offsetWidth }}
        >
          <Paper elevation={3} sx={{ maxHeight: 200, overflow: 'auto', mt: '4px' }}>
            {suggestions.map((label, idx) => (
              <Box
                key={label.id}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => addLabel(label)}
                onMouseEnter={() => setHighlightedIndex(idx)}
                sx={{
                  px: 1.5,
                  py: '6px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  backgroundColor: idx === highlightedIndex ? 'action.hover' : 'transparent',
                  '&:hover': { backgroundColor: 'action.hover' },
                }}
              >
                <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: label.color, flexShrink: 0 }} />
                <Typography variant="body2">{label.name}</Typography>
              </Box>
            ))}
          </Paper>
        </Popper>
      </Box>
    </ClickAwayListener>
  );
};
