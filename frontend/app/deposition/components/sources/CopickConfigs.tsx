'use client';

import { useEffect, useRef, useState } from 'react';
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
  const [copied, setCopied] = useState<string | null>(null);
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => clearTimeout(copyTimer.current ?? undefined), []);

  const copyPath = (value: string) => {
    navigator.clipboard?.writeText(value).catch(() => undefined);
    setCopied(value);
    clearTimeout(copyTimer.current ?? undefined);
    copyTimer.current = setTimeout(() => setCopied((c) => (c === value ? null : c)), 1200);
  };
  const configs = row.selected_copick_runs;
  const available = (copick.data ?? []).filter((r) => !configs.includes(r.name));
  const byName = new Map((copick.data ?? []).map((r) => [r.name, r]));

  return (
    <Box sx={{ bgcolor: 'grey.50', borderRadius: 2, border: '1px solid', borderColor: 'divider', p: 2, mt: 1 }}>
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          justifyContent: 'space-between',
          alignItems: { xs: 'flex-start', sm: 'center' },
          gap: 1,
          mb: 1.5,
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          <Box component="span" sx={{ letterSpacing: 0.6, textTransform: 'uppercase', fontSize: '0.7rem' }}>
            Copick configs
          </Box>{' '}
          <Typography component="span" variant="body2" color="text.secondary" sx={{ fontWeight: 400 }}>
            you&rsquo;ll pick annotations later
          </Typography>
        </Typography>
        <Button
          sdsType="primary"
          sdsStyle="minimal"
          size="small"
          startIcon={<Icon sdsIcon="Plus" sdsSize="xs" />}
          disabled={readOnly || !row.msi_session_name}
          onClick={(e) => setAnchor(e.currentTarget)}
          sx={{ flexShrink: 0, textTransform: 'none', fontWeight: 600 }}
        >
          Add copick config
        </Button>
      </Box>

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
                fontSize: '0.7rem',
                color: 'text.secondary',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
              title={path}
            >
              {path}
            </Typography>
            <Chip size="small" label={c} sx={outlineChipSx('info.main')} />
            <IconButton
              size="small"
              onClick={() => copyPath(path)}
              aria-label={`Copy path for ${c}`}
              title={copied === path ? 'Copied!' : 'Copy path'}
              sx={{ color: copied === path ? 'success.main' : 'text.secondary' }}
            >
              <Icon
                sdsIcon={copied === path ? 'Check' : 'Copy'}
                sdsSize="xs"
                color={copied === path ? 'green' : 'gray'}
                shade={copied === path ? 400 : 500}
              />
            </IconButton>
            <IconButton
              size="small"
              disabled={readOnly}
              onClick={() => onChange({ selected_copick_runs: configs.filter((x) => x !== c) })}
              aria-label={`Remove ${c}`}
              sx={{ color: 'error.main' }}
            >
              <Icon sdsIcon="TrashCan" sdsSize="xs" color="red" shade={400} />
            </IconButton>
          </Box>
        );
      })}

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
