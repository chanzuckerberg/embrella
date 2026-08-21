import { useContext, useRef, useState } from 'react';
import { Chip, IconButton, InputAdornment, TextField } from '@mui/material';
import CancelIcon from '@mui/icons-material/Cancel';
import SearchIcon from '@mui/icons-material/Search';

import {
  TableDispatchContext,
  TableStateActionTypes,
  TableStateContext,
} from '@app/common/components/TableStateProvider/TableStateProvider';

import { SessionFilterCategory } from '../types';

/**
 * Full-width search above the table, in the same position and shape as Grid
 * Inventory's.
 *
 * GridsView's SearchBar itself isn't reusable — its suggestion categories and
 * `project:`/`box:` qualifiers are grid-specific
 */

// Ordered as they should read in the chip row.
const TAG_CATEGORIES: SessionFilterCategory[] = [
  'project',
  'user',
  'processingSoftware',
  'scope',
  'workflow',
  'search',
];

const CATEGORY_LABELS: Record<SessionFilterCategory, string> = {
  project: 'Project',
  user: 'User',
  processingSoftware: 'Software',
  scope: 'Scope',
  workflow: 'Workflow',
  search: 'Search',
};

const CATEGORY_COLORS: Record<SessionFilterCategory, { bg: string; border: string; text: string }> = {
  project: { bg: '#e3f2fd', border: '#90caf9', text: '#1565c0' },
  user: { bg: '#f3e5f5', border: '#ce93d8', text: '#7b1fa2' },
  processingSoftware: { bg: '#e8f5e9', border: '#a5d6a7', text: '#2e7d32' },
  scope: { bg: '#ede7f6', border: '#b39ddb', text: '#4527a0' },
  workflow: { bg: '#e0f7fa', border: '#80deea', text: '#00695c' },
  search: { bg: '#f5f5f5', border: '#bdbdbd', text: '#424242' },
};

interface FilterTag {
  category: SessionFilterCategory;
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

export const SessionSearchBar = (): React.JSX.Element => {
  const { filterState } = useContext(TableStateContext);
  const dispatch = useContext(TableDispatchContext);
  const inputRef = useRef<HTMLInputElement>(null);
  const [term, setTerm] = useState('');

  const activeTags = getActiveTags(filterState as Record<string, unknown>);
  const hasContent = activeTags.length > 0 || term.length > 0;

  const setCategory = (category: SessionFilterCategory, value: string[]) => {
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
      placeholder={activeTags.length > 0 ? 'Add another filter...' : 'Search sessions...'}
      size="small"
      fullWidth
      inputProps={{ 'aria-label': 'Search sessions' }}
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
