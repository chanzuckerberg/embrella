'use client';

import { useState, type ReactNode } from 'react';
import { Icon } from '@czi-sds/components';
import { Box, Collapse, Typography } from '@mui/material';

export function CollapsibleSection({
  title,
  summary,
  defaultOpen = false,
  children,
}: {
  title: string;
  summary?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
      <Box
        component="button"
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        sx={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 2,
          py: 1.5,
          bgcolor: 'transparent',
          border: 0,
          cursor: 'pointer',
          textAlign: 'left',
          font: 'inherit',
        }}
      >
        <Icon sdsIcon={open ? 'ChevronDown' : 'ChevronRight'} sdsSize="xs" color="gray" />
        <Typography variant="subtitle2" sx={{ fontWeight: 700, flex: 1 }}>
          {title}
        </Typography>
        {summary != null && (
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {summary}
          </Typography>
        )}
      </Box>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ px: 2, pb: 2, pt: 0.5 }}>{children}</Box>
      </Collapse>
    </Box>
  );
}
