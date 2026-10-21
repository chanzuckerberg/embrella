'use client';

import React from 'react';
import { format, isToday, isYesterday } from 'date-fns';
import { Box, Chip, Tooltip, Typography } from '@mui/material';
import type { SvgIconComponent } from '@mui/icons-material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import BiotechIcon from '@mui/icons-material/Biotech';
import ContentCutIcon from '@mui/icons-material/ContentCut';
import DeleteForeverIcon from '@mui/icons-material/DeleteForever';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import DriveFileMoveOutlinedIcon from '@mui/icons-material/DriveFileMoveOutlined';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';
import LabelOffOutlinedIcon from '@mui/icons-material/LabelOffOutlined';
import LabelOutlinedIcon from '@mui/icons-material/LabelOutlined';
import MemoryIcon from '@mui/icons-material/Memory';
import RestoreFromTrashIcon from '@mui/icons-material/RestoreFromTrash';
import {
  Timeline as MuiTimeline,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineItem,
  TimelineSeparator,
  timelineItemClasses,
} from '@mui/lab';
import { TimelineEntry, TimelineKind, TimelineSubject } from '@app/common/types/timeline';
import { FORMAT_PATTERN, formatDate, formatTimeAgo } from '@app/common/utils/format';
import { LABEL_GROUP_TITLE, TimelineLabel, groupLabels } from './groupLabels';

const KIND_ICON: Record<TimelineKind, SvgIconComponent> = {
  [TimelineKind.CREATED]: AddCircleOutlineIcon,
  [TimelineKind.EDITED]: EditOutlinedIcon,
  [TimelineKind.MOVED]: DriveFileMoveOutlinedIcon,
  [TimelineKind.TRASHED]: DeleteOutlineIcon,
  [TimelineKind.RESTORED]: RestoreFromTrashIcon,
  [TimelineKind.CLIPPED]: ContentCutIcon,
  [TimelineKind.UNCLIPPED]: ContentCutIcon,
  [TimelineKind.LABEL_ADDED]: LabelOutlinedIcon,
  [TimelineKind.LABEL_REMOVED]: LabelOffOutlinedIcon,
  [TimelineKind.DELETED]: DeleteForeverIcon,
};

// Non-grid subjects get their own icon, e.g. a proc run "created" is a run, not a new grid
// The grid's container (box, puck, cane, dewar) moved with the grid inside, vs. the grid itself moving
const CONTAINER_MOVE_ICON = Inventory2OutlinedIcon;

const SUBJECT_ICON: Partial<Record<TimelineSubject, SvgIconComponent>> = {
  [TimelineSubject.MSI_SESSION]: BiotechIcon,
  [TimelineSubject.PROC_RUN]: MemoryIcon,
};

const SUBJECT_LABEL: Record<TimelineSubject, string> = {
  [TimelineSubject.GRID]: 'Grid',
  [TimelineSubject.MSI_SESSION]: 'MSI Session',
  [TimelineSubject.PROC_RUN]: 'Proc Run',
};

const LABEL_KINDS = new Set([TimelineKind.LABEL_ADDED, TimelineKind.LABEL_REMOVED]);

// Approximate rendered row height, used to cap the list at `maxVisible` rows
const ROW_HEIGHT_PX = 70;

// Show half of the next row so the cut-off itself hints at scrolling
const PEEK_ROWS = 0.5;

/**
 * Scroll shadows: a soft edge appears only where more rows are hidden (top once scrolled, bottom until the end).
 * Covers ("local", move with content) hide the shadows ("scroll", pinned to the box) at the ends.
 */
const scrollShadows = (paper: string) => ({
  background: `
    linear-gradient(${paper} 30%, transparent) top / 100% 40px local,
    linear-gradient(transparent, ${paper} 70%) bottom / 100% 40px local,
    radial-gradient(farthest-side at 50% 0, rgba(0,0,0,0.15), transparent) top / 100% 14px scroll,
    radial-gradient(farthest-side at 50% 100%, rgba(0,0,0,0.15), transparent) bottom / 100% 14px scroll`,
  backgroundRepeat: 'no-repeat',
});

// Day header, in local time: "Today", "Yesterday", else e.g. "Oct 16 2026"
const dayLabel = (at: string): string => {
  const date = new Date(at);

  if (isToday(date)) return 'Today';
  if (isYesterday(date)) return 'Yesterday';

  return format(date, FORMAT_PATTERN.MMM_D_YYYY);
};

interface TimelineProps {
  entries: TimelineEntry[];
  emptyText?: string;
  // Scroll after this many rows, e.g. 8; unset = no cap
  maxVisible?: number;
}

/**
 * Vertical history, newest first. One dot per entry: icon by kind (or subject), label color for label entries.
 * Batches of label changes collapse into one row (see groupLabels).
 */
export const Timeline: React.FC<TimelineProps> = ({ entries: raw, emptyText = 'No history yet.', maxVisible }) => {
  const entries = groupLabels(raw);

  if (entries.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyText}
      </Typography>
    );
  }

  const capped = !!maxVisible && entries.length > maxVisible;

  // Drop the default left gutter: no opposite content
  return (
    <>
      <MuiTimeline
        sx={(theme) => ({
          // Strings bypass theme spacing, where SDS maps 0 to 8px (a gap above sticky day headers)
          padding: '0px',
          margin: '0px',
          [`& .${timelineItemClasses.root}:before`]: { flex: 0, padding: '0px' },
          ...(capped && {
            maxHeight: (maxVisible + PEEK_ROWS) * ROW_HEIGHT_PX,
            overflowY: 'auto',
            flexWrap: 'nowrap',
            ...scrollShadows(theme.palette.background.paper),
          }),
        })}
      >
        {entries.map((entry, i) => {
          // New day header whenever the day changes, e.g. "Today" … "Oct 16 2026"
          const day = dayLabel(entry.at);
          const newDay = i === 0 || day !== dayLabel(entries[i - 1].at);

          return (
            <React.Fragment key={`${entry.subject}-${entry.subject_id}-${entry.at}-${i}`}>
              {newDay && <DayHeader label={day} />}
              <TimelineRow entry={entry} last={i === entries.length - 1} />
            </React.Fragment>
          );
        })}
      </MuiTimeline>

      {capped && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mt: '4px' }}>
          {entries.length} entries
        </Typography>
      )}
    </>
  );
};

// Sticks to the top while its day scrolls by
const DayHeader: React.FC<{ label: string }> = ({ label }) => (
  <Box
    component="li"
    sx={{ listStyle: 'none', position: 'sticky', top: 0, zIndex: 1, bgcolor: 'background.paper', py: '4px' }}
  >
    <Typography variant="overline" color="text.secondary">
      {label}
    </Typography>
  </Box>
);

const TimelineRow: React.FC<{ entry: TimelineEntry; last: boolean }> = ({ entry, last }) => {
  const containerMove = entry.kind === TimelineKind.MOVED && entry.detail.via !== TimelineSubject.GRID;
  const Icon = SUBJECT_ICON[entry.subject] ?? (containerMove ? CONTAINER_MOVE_ICON : KIND_ICON[entry.kind]);
  const labelColor = LABEL_KINDS.has(entry.kind) ? (entry.detail.color as string | null) : null;

  return (
    <TimelineItem>
      <TimelineSeparator>
        <TimelineDot variant="outlined" sx={labelColor ? { borderColor: labelColor } : undefined}>
          <Icon sx={{ fontSize: 16, color: labelColor ?? undefined }} />
        </TimelineDot>
        {!last && <TimelineConnector />}
      </TimelineSeparator>

      <TimelineContent sx={{ py: '10px' }}>
        {entry.detail.labels ? (
          <LabelGroup kind={entry.kind} labels={entry.detail.labels as TimelineLabel[]} />
        ) : (
          <Typography variant="body2">{entry.summary}</Typography>
        )}

        <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px', mt: '2px' }}>
          {entry.subject !== TimelineSubject.GRID && (
            <Chip label={SUBJECT_LABEL[entry.subject]} size="small" variant="outlined" />
          )}
          {entry.user && (
            <Typography variant="caption" color="text.secondary">
              {entry.user}
            </Typography>
          )}
          <Tooltip title={formatDate(entry.at, FORMAT_PATTERN.MMM_D_YYYY_HH_MM)}>
            <Typography variant="caption" color="text.secondary">
              {formatTimeAgo(entry.at)}
            </Typography>
          </Tooltip>
        </Box>
      </TimelineContent>
    </TimelineItem>
  );
};

// e.g. "Labels added: ● TBS ● P1", each dot in its label color
const LabelGroup: React.FC<{ kind: TimelineKind; labels: TimelineLabel[] }> = ({ kind, labels }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', columnGap: '10px' }}>
    <Typography variant="body2">{LABEL_GROUP_TITLE[kind]}:</Typography>
    {labels.map(({ label, color }, i) => (
      <Box key={`${label}-${i}`} sx={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: color ?? 'text.disabled' }} />
        <Typography variant="body2">{label ?? 'unknown'}</Typography>
      </Box>
    ))}
  </Box>
);
