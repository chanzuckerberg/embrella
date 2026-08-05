'use client';

import { useState } from 'react';
import { Button, Icon } from '@czi-sds/components';
import { Box, Chip, IconButton, Menu, MenuItem, Typography } from '@mui/material';

import { useCopickRuns } from '../../hooks/useSources';
import { outlineChipSx } from './chipStyles';
import type { SourceRow } from './types';

export function CopickConfigs({
  row,
  readOnly,
  onChange,
}: {
  row: SourceRow;
  readOnly: boolean;
  onChange: (patch: Partial<SourceRow>) => void;
}) {
  const copick = useCopickRuns(row.msi_session_name);
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const configs = row.selected_copick_runs;
  const available = (copick.data ?? []).filter((r) => !configs.includes(r.name));
  const byName = new Map((copick.data ?? []).map((r) => [r.name, r]));

  return (
    <Box sx={{ bgcolor: 'grey.50', borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 2, mt: 1 }}>
      <Typography variant="body2" sx={{ fontWeight: 700, mb: 1.5 }}>
        <Box component="span" sx={{ letterSpacing: 0.6, textTransform: 'uppercase', fontSize: '0.7rem' }}>
          Copick configs
        </Box>{' '}
        <Typography component="span" variant="body2" color="text.secondary" sx={{ fontWeight: 400 }}>
          {configs.length} selected · included in Step 6
        </Typography>
      </Typography>

      {configs.map((c) => {
        const opt = byName.get(c);
        const path = opt?.description || opt?.label || c;
        return (
          <Box
            key={c}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              bgcolor: 'background.paper',
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1.5,
              px: 1.5,
              py: 1,
              mb: 1,
            }}
          >
            <Typography
              variant="body2"
              sx={{
                flex: 1,
                minWidth: 0,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                fontSize: '0.8rem',
                color: 'text.secondary',
              }}
              noWrap
              title={path}
            >
              {path}
            </Typography>
            <Chip size="small" label={c} sx={outlineChipSx('info.main')} />
            <IconButton
              size="small"
              disabled={readOnly}
              onClick={() => onChange({ selected_copick_runs: configs.filter((x) => x !== c) })}
              aria-label={`Remove ${c}`}
              sx={{ color: 'error.main' }}
            >
              <Icon sdsIcon="TrashCan" sdsSize="xs" />
            </IconButton>
          </Box>
        );
      })}

      <Button
        sdsType="primary"
        sdsStyle="outline"
        startIcon={<Icon sdsIcon="Plus" sdsSize="xs" />}
        disabled={readOnly || !row.msi_session_name}
        onClick={(e) => setAnchor(e.currentTarget)}
        sx={{ mt: configs.length ? 0.5 : 0, textTransform: 'none', fontWeight: 600 }}
      >
        Add copick config
      </Button>
      <Menu anchorEl={anchor} open={!!anchor} onClose={() => setAnchor(null)}>
        {copick.isFetching && <MenuItem disabled>Loading…</MenuItem>}
        {available.map((r) => (
          <MenuItem
            key={r.name}
            onClick={() => {
              onChange({ selected_copick_runs: [...configs, r.name] });
              setAnchor(null);
            }}
          >
            {r.label || r.name}
          </MenuItem>
        ))}
        {!copick.isFetching && available.length === 0 && <MenuItem disabled>No copick configs found</MenuItem>}
      </Menu>
    </Box>
  );
}
