import { useContext, useRef, useState } from 'react';
import { Chip, IconButton, InputAdornment, TextField } from '@mui/material';
import CancelIcon from '@mui/icons-material/Cancel';
import SearchIcon from '@mui/icons-material/Search';

import {
  TableDispatchContext,
  TableStateActionTypes,
  TableStateContext,
} from '@app/common/components/TableStateProvider/TableStateProvider';

import { StorageFilterCategory } from '../types';

/**
 * Full-width search above the table, matching the session browser's.
 *
 * Search is a bar rather than a sidebar field because it is the fastest way to
 * reach a known session name, and the sidebar is for narrowing by facet.
 */

// Ordered as they should read in the chip row.
const TAG_CATEGORIES: StorageFilterCategory[] = ['project', 'user', 'owner', 'processingSoftware', 'search'];

const CATEGORY_LABELS: Record<StorageFilterCategory, string> = {
  project: 'Project',
  user: 'User',
  owner: 'Owner',
  processingSoftware: 'Software',
  search: 'Search',
};

const CATEGORY_COLORS: Record<StorageFilterCategory, { bg: string; border: string; text: string }> = {
  project: { bg: '#e3f2fd', border: '#90caf9', text: '#1565c0' },
  user: { bg: '#f3e5f5', border: '#ce93d8', text: '#7b1fa2' },
  owner: { bg: '#e0f7fa', border: '#80deea', text: '#00695c' },
  processingSoftware: { bg: '#e8f5e9', border: '#a5d6a7', text: '#2e7d32' },
  search: { bg: '#f5f5f5', border: '#bdbdbd', text: '#424242' },
};

interface FilterTag {
  category: StorageFilterCategory;
  value: string;
}

function getActiveTags(filterState: Record<string, unknown>): FilterTag[] {
  const tags: FilterTag[] = [];

  for (const category of TAG_CATEGORIES) {
    const raw = filterState[category];
    if (raw === undefined || raw === null) continue;

    for (const value of Array.isArray(raw) ? raw : [raw]) {
      if (value !== null && value !== undefined && String(value).length > 0) {
        tags.push({ category, value: String(value) });
      }
    }
  }

  return tags;
}

export const StorageSearchBar = (): React.JSX.Element => {
  const { filterState } = useContext(TableStateContext);
  const dispatch = useContext(TableDispatchContext);
  const inputRef = useRef<HTMLInputElement>(null);
  const [term, setTerm] = useState('');

  const activeTags = getActiveTags(filterState as Record<string, unknown>);
  const hasContent = activeTags.length > 0 || term.length > 0;

  const setCategory = (category: StorageFilterCategory, value: string[]) => {
    dispatch({
      payload: { categoryFilter: { category, value } },
      type: TableStateActionTypes.UpdateFilter,
    });
  };

  const handleSubmit = () => {
    const trimmed = term.trim();
    if (!trimmed) return;

    const current = Array.isArray(filterState.search) ? (filterState.search as string[]) : [];
    if (!current.includes(trimmed)) {
      setCategory('search', [...current, trimmed]);
    }
    setTerm('');
  };

  const handleRemoveTag = (tag: FilterTag) => {
    const raw = filterState[tag.category];
    const remaining = Array.isArray(raw) ? raw.map(String).filter((v) => v !== tag.value) : [];
    setCategory(tag.category, remaining);
    inputRef.current?.focus();
  };

  const handleClearAll = () => {
    dispatch({ type: TableStateActionTypes.ClearAllFilters });
    setTerm('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    } else if (e.key === 'Backspace' && term === '' && activeTags.length > 0) {
      handleRemoveTag(activeTags[activeTags.length - 1]);
    }
  };

  const tagChips = activeTags.map((tag) => {
    const colors = CATEGORY_COLORS[tag.category];
    return (
      <Chip
        key={`${tag.category}-${tag.value}`}
        label={`${CATEGORY_LABELS[tag.category]}: ${tag.value}`}
        size="small"
        onDelete={() => handleRemoveTag(tag)}
        onMouseDown={(e) => e.preventDefault()}
        sx={{
          backgroundColor: colors.bg,
          borderColor: colors.border,
          color: colors.text,
          borderWidth: 1,
          borderStyle: 'solid',
          height: 24,
          '& .MuiChip-deleteIcon': { color: colors.text, fontSize: 16, '&:hover': { color: colors.text } },
        }}
      />
    );
  });

  return (
    <TextField
      inputRef={inputRef}
      value={term}
      onChange={(e) => setTerm(e.target.value)}
      onKeyDown={handleKeyDown}
      placeholder={activeTags.length > 0 ? 'Add another filter...' : 'Search sessions, software or runs...'}
      size="small"
      fullWidth
      inputProps={{ 'aria-label': 'Search storage' }}
      InputProps={{
        startAdornment: (
          <>
            <InputAdornment position="start" sx={{ mr: '4px' }}>
              <SearchIcon fontSize="small" sx={{ color: 'action.active' }} />
            </InputAdornment>
            {tagChips}
          </>
        ),
        endAdornment: hasContent ? (
          <InputAdornment position="end">
            <IconButton size="small" onClick={handleClearAll} aria-label="Clear all filters">
              <CancelIcon fontSize="small" sx={{ color: 'action.active' }} />
            </IconButton>
          </InputAdornment>
        ) : undefined,
      }}
      sx={{
        '& .MuiOutlinedInput-root': {
          display: 'flex',
          flexWrap: 'nowrap',
          alignItems: 'center',
          gap: '4px',
          overflowX: 'auto',
          '& input': { flexGrow: 1, flexShrink: 1, minWidth: 120 },
        },
      }}
    />
  );
};
