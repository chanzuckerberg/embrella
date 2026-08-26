'use client';

import { Box, Button, Typography } from '@mui/material';

import { YamlHighlight } from './YamlHighlight';

export function YamlPreview({ yaml, title, onClose }: { yaml: string; title?: string; onClose: () => void }) {
  return (
    <Box
      sx={{
        position: 'sticky',
        top: 0,
        alignSelf: 'start',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: 'calc(100vh - 300px)',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          px: 1.5,
          py: 1,
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }} noWrap>
            dataprep_config.yaml
          </Typography>
          {title && (
            <Typography variant="caption" color="text.secondary" noWrap>
              {title}
            </Typography>
          )}
        </Box>
        <Button size="small" onClick={onClose} sx={{ textTransform: 'none', color: 'text.secondary', flexShrink: 0 }}>
          Close
        </Button>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', bgcolor: '#0d1117' }}>
        <YamlHighlight yaml={yaml} />
      </Box>
    </Box>
  );
}
