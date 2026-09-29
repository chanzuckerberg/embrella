'use client';

import { useState } from 'react';
import { Icon } from '@czi-sds/components';
import { Box, Chip, Collapse, IconButton, Paper, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';

export function SectionCard({
  title,
  subtitle,
  badge,
  badgeTone = 'default',
  sectionKey,
  action,
  info,
  collapsible = false,
  defaultExpanded = true,
  innerRef,
  children,
}: {
  title: string;
  subtitle?: string;
  badge?: string;
  badgeTone?: 'default' | 'primary';
  sectionKey: string;
  action?: React.ReactNode;
  info?: React.ReactNode;
  collapsible?: boolean;
  defaultExpanded?: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
  children: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <Paper
      ref={innerRef}
      data-key={sectionKey}
      variant="outlined"
      sx={{
        p: 3,
        borderRadius: 2,
        scrollMarginTop: 16,
        bgcolor: 'background.paper',
        borderColor: 'divider',
        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: !collapsible || expanded ? 2.5 : 0,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            ...(collapsible
              ? {
                  cursor: 'pointer',
                  flex: 1,
                  minWidth: 0,
                }
              : {}),
          }}
          onClick={collapsible ? () => setExpanded((v) => !v) : undefined}
          role={collapsible ? 'button' : undefined}
          aria-expanded={collapsible ? expanded : undefined}
        >
          {collapsible && (
            <IconButton
              size="small"
              aria-label={expanded ? `Collapse ${title}` : `Expand ${title}`}
              onClick={(e) => {
                e.stopPropagation();
                setExpanded((v) => !v);
              }}
              sx={{
                transform: expanded ? 'rotate(0deg)' : 'rotate(-90deg)',
                transition: 'transform 120ms',
              }}
            >
              <Icon sdsIcon="ChevronDown" sdsSize="xs" />
            </IconButton>
          )}
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.125rem', lineHeight: 1.3 }}>
            {title}
          </Typography>
          {info && (
            <Box component="span" onClick={(e) => e.stopPropagation()} sx={{ display: 'inline-flex' }}>
              {info}
            </Box>
          )}
          {badge && (
            <Chip
              label={badge}
              size="small"
              sx={{
                height: 22,
                fontWeight: 600,
                ...(badgeTone === 'primary'
                  ? {
                      bgcolor: (t) => alpha(t.palette.primary.main, 0.12),
                      color: 'primary.main',
                    }
                  : {
                      bgcolor: 'grey.100',
                      color: 'text.secondary',
                    }),
              }}
            />
          )}
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        {action}
      </Box>
      {collapsible ? (
        <Collapse in={expanded}>
          <Stack spacing={2.5}>{children}</Stack>
        </Collapse>
      ) : (
        <Stack spacing={2.5}>{children}</Stack>
      )}
    </Paper>
  );
}
