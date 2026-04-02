import {
  TableDispatchContext,
  TableStateActionTypes,
  TableStateContext,
} from '@app/common/components/TableStateProvider/TableStateProvider';
import { API, DJANGO_URL } from '@app/common/constants/api';
import SearchIcon from '@mui/icons-material/Search';
import CancelIcon from '@mui/icons-material/Cancel';
import {
  Popper,
  Paper,
  Typography,
  Chip,
  ClickAwayListener,
  TextField,
  InputAdornment,
  IconButton,
} from '@mui/material';
import { useCallback, useContext, useEffect, useRef, useState } from 'react';

interface Suggestion {
  value: string;
  category: 'grid' | 'project' | 'user' | 'sample' | 'msiSession' | 'label';
}

interface FilterTag {
  category: string;
  value: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  grid: 'Grid',
  gridBox: 'Grid Box',
  project: 'Project',
  user: 'User',
  sample: 'Sample',
  msiSession: 'MSI',
  label: 'Label',
  search: 'Search',
};

const QUALIFIER_MAP: Record<string, string> = {
  'project:': 'project',
  'user:': 'user',
  'sample:': 'sample',
  'grid:': 'grid',
  'box:': 'gridBox',
  'session:': 'msiSession',
  'label:': 'label',
};

const CATEGORY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  project: { bg: '#e3f2fd', border: '#90caf9', text: '#1565c0' },
  user: { bg: '#f3e5f5', border: '#ce93d8', text: '#7b1fa2' },
  sample: { bg: '#e8f5e9', border: '#a5d6a7', text: '#2e7d32' },
  grid: { bg: '#fff3e0', border: '#ffcc80', text: '#e65100' },
  gridBox: { bg: '#fce4ec', border: '#f48fb1', text: '#c62828' },
  msiSession: { bg: '#e0f7fa', border: '#80deea', text: '#00695c' },
  label: { bg: '#fff8e1', border: '#ffd54f', text: '#f57f17' },
  search: { bg: '#f5f5f5', border: '#bdbdbd', text: '#424242' },
};

const SEARCHBAR_CATEGORIES = ['project', 'user', 'sample', 'msiSession', 'label', 'search'];

/** Map frontend-only categories to the backend filter category they dispatch as. */
const CATEGORY_DISPATCH_MAP: Record<string, string> = {
  grid: 'search',
  gridBox: 'search',
};

function getTagsFromFilterState(filterState: Record<string, unknown>): FilterTag[] {
  const tags: FilterTag[] = [];
  for (const category of SEARCHBAR_CATEGORIES) {
    const val = filterState[category];
    if (val === undefined || val === null) continue;
    const values = Array.isArray(val) ? val : [val];
    for (const v of values) {
      if (v !== null && v !== undefined && String(v).length > 0) {
        tags.push({ category, value: String(v) });
      }
    }
  }
  return tags;
}

interface SearchBarProps {
  placeholder?: string;
  suggestionsApi?: API;
}

export const SearchBar = ({
  placeholder = 'Search grids...',
  suggestionsApi = API.GRIDS_SEARCH_SUGGESTIONS,
}: SearchBarProps) => {
  const tableState = useContext(TableStateContext);
  const dispatchTableState = useContext(TableDispatchContext);
  const [localInput, setLocalInput] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const anchorRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const blurStampRef = useRef(0);

  const activeTags = getTagsFromFilterState(tableState.filterState as Record<string, unknown>);
  const hasContent = activeTags.length > 0 || localInput.length > 0;

  const bumpStamp = () => {
    blurStampRef.current += 1;
  };

  const fetchSuggestions = useCallback(
    (term: string) => {
      if (term.length < 1) {
        setSuggestions([]);
        return;
      }
      fetch(`${DJANGO_URL}${suggestionsApi}?term=${encodeURIComponent(term)}`, { credentials: 'include' })
        .then((res) => res.json())
        .then((data) => setSuggestions(data.suggestions ?? []))
        .catch(() => setSuggestions([]));
    },
    [suggestionsApi]
  );

  // Reset highlighted index when suggestions change
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [suggestions]);

  useEffect(() => {
    let searchTerm = localInput;
    for (const prefix of Object.keys(QUALIFIER_MAP)) {
      if (searchTerm.toLowerCase().startsWith(prefix)) {
        searchTerm = searchTerm.slice(prefix.length).trim();
        break;
      }
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(searchTerm), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [localInput, fetchSuggestions]);

  const dispatchFilter = (category: string, value: string) => {
    const existing = tableState.filterState[category as keyof typeof tableState.filterState];
    const current = Array.isArray(existing) ? (existing as string[]) : [];
    if (current.includes(value)) return;
    dispatchTableState({
      payload: {
        categoryFilter: {
          category: category as 'project' | 'user' | 'sample' | 'msiSession' | 'search',
          value: [...current, value],
        },
      },
      type: TableStateActionTypes.UpdateFilter,
    });
  };

  const handleSubmit = () => {
    const trimmed = localInput.trim();
    if (!trimmed) return;

    for (const [prefix, rawCategory] of Object.entries(QUALIFIER_MAP)) {
      if (trimmed.toLowerCase().startsWith(prefix)) {
        const term = trimmed.slice(prefix.length).trim();
        if (term) {
          dispatchFilter(CATEGORY_DISPATCH_MAP[rawCategory] ?? rawCategory, term);
          setLocalInput('');
          setShowDropdown(false);
          return;
        }
      }
    }

    dispatchFilter('search', trimmed);
    setLocalInput('');
    setShowDropdown(false);
  };

  const handleClearAll = () => {
    dispatchTableState({ type: TableStateActionTypes.ClearAllFilters });
    setLocalInput('');
    setSuggestions([]);
    setShowDropdown(false);
  };

  const handleSuggestionClick = (suggestion: Suggestion) => {
    bumpStamp();
    const category = CATEGORY_DISPATCH_MAP[suggestion.category] ?? suggestion.category;
    dispatchFilter(category, suggestion.value);
    setLocalInput('');
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const handleRemoveTag = (tag: FilterTag) => {
    const filterVal = tableState.filterState[tag.category as keyof typeof tableState.filterState];
    if (Array.isArray(filterVal)) {
      const remaining = (filterVal as string[]).filter((v) => String(v) !== tag.value);
      dispatchTableState({
        payload: {
          categoryFilter: {
            category: tag.category as 'project' | 'user' | 'sample' | 'msiSession' | 'search',
            value: remaining,
          },
        },
        type: TableStateActionTypes.UpdateFilter,
      });
    } else {
      dispatchTableState({
        payload: {
          categoryFilter: {
            category: tag.category as 'project' | 'user' | 'sample' | 'msiSession' | 'search',
            value: [],
          },
        },
        type: TableStateActionTypes.UpdateFilter,
      });
    }
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev < flatSuggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : flatSuggestions.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < flatSuggestions.length) {
        handleSuggestionClick(flatSuggestions[highlightedIndex]);
        setHighlightedIndex(-1);
      } else {
        handleSubmit();
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      setHighlightedIndex(-1);
    } else if (e.key === 'Backspace' && localInput === '' && activeTags.length > 0) {
      handleRemoveTag(activeTags[activeTags.length - 1]);
    }
  };

  const SUGGESTION_ORDER = ['project', 'user', 'sample', 'msiSession', 'label', 'grid'];

  const groupedSuggestions = suggestions.reduce(
    (acc, s) => {
      if (!acc[s.category]) acc[s.category] = [];
      acc[s.category].push(s);
      return acc;
    },
    {} as Record<string, Suggestion[]>
  );

  const sortedSuggestionEntries = Object.entries(groupedSuggestions).sort(
    ([a], [b]) => (SUGGESTION_ORDER.indexOf(a) ?? 99) - (SUGGESTION_ORDER.indexOf(b) ?? 99)
  );

  // Flat list of all suggestions in render order for keyboard navigation
  const flatSuggestions = sortedSuggestionEntries.flatMap(([, items]) => items);

  const tagChips = activeTags.map((tag) => {
    const colors = CATEGORY_COLORS[tag.category] ?? CATEGORY_COLORS.search;
    const label = CATEGORY_LABELS[tag.category] ?? tag.category;
    return (
      <Chip
        key={`${tag.category}-${tag.value}`}
        label={`${label}: ${tag.value}`}
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
    <ClickAwayListener onClickAway={() => setShowDropdown(false)}>
      <div ref={anchorRef} className="px-3 pt-3 pb-1">
        <TextField
          inputRef={inputRef}
          value={localInput}
          onChange={(e) => {
            setLocalInput(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => {
            bumpStamp();
            setShowDropdown(true);
          }}
          onBlur={() => {
            const stamp = blurStampRef.current;
            setTimeout(() => {
              if (blurStampRef.current !== stamp) return;
              setShowDropdown(false);
            }, 200);
          }}
          onKeyDown={handleKeyDown}
          placeholder={activeTags.length > 0 ? 'Add another filter...' : placeholder}
          size="small"
          fullWidth
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

        <Popper
          open={showDropdown && (suggestions.length > 0 || localInput.length === 0)}
          anchorEl={anchorRef.current}
          placement="bottom-start"
          style={{ zIndex: 1300, width: anchorRef.current?.offsetWidth }}
        >
          <Paper elevation={3} className="mt-1 max-h-[320px] overflow-y-auto" role="listbox">
            {(() => {
              let flatIndex = 0;
              return sortedSuggestionEntries.map(([category, items]) => {
                const colors = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.search;
                return (
                  <div key={category} className="px-3 py-1">
                    <Typography variant="caption" className="!font-semibold uppercase" style={{ color: colors.text }}>
                      {CATEGORY_LABELS[category] ?? category}
                    </Typography>
                    {items.map((item) => {
                      const idx = flatIndex++;
                      const isHighlighted = idx === highlightedIndex;
                      return (
                        <div
                          key={`${category}-${item.value}`}
                          role="option"
                          aria-selected={isHighlighted}
                          className={`cursor-pointer rounded px-2 py-1 ${isHighlighted ? 'bg-gray-200' : 'hover:bg-gray-100'}`}
                          onMouseDown={(e) => e.preventDefault()}
                          onMouseEnter={() => setHighlightedIndex(idx)}
                          onClick={() => handleSuggestionClick(item)}
                        >
                          <Typography variant="body1">{item.value}</Typography>
                        </div>
                      );
                    })}
                  </div>
                );
              });
            })()}
          </Paper>
        </Popper>
      </div>
    </ClickAwayListener>
  );
};
