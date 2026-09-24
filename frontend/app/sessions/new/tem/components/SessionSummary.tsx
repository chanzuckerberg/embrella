import React from 'react';
import { Box, Typography } from '@mui/material';
import { CreatedSession, RolePath } from '../types';

const CODE_SX = {
  fontFamily: 'monospace',
  bgcolor: 'grey.100',
  px: 1,
  py: 0.5,
  borderRadius: 1,
  wordBreak: 'break-all',
} as const;

/** Directory and filename pattern: two halves resolved from different config, shown apart. */
function PathRow({ label, path }: { label: string; path: RolePath }) {
  if (!path?.directory) return null;
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={CODE_SX}>
        {path.directory}
      </Typography>
      {path.pattern && (
        <Typography variant="body2" sx={{ ...CODE_SX, mt: 0.25 }} color="text.secondary">
          files: {path.pattern}
        </Typography>
      )}
    </Box>
  );
}

function usageLabel(used: boolean | null): string {
  if (used == null) return 'Unknown';
  return used ? 'Yes' : 'No';
}

interface SessionSummaryProps {
  session: CreatedSession;
  /** Rendered between the identity rows and the paths, e.g. a review notice. */
  notice?: React.ReactNode;
}

/**
 * A session at a glance: name, project, grid, plan, and where each data role lands.
 * Shared by the created-session dialog and the launch form's session accordion.
 */
export function SessionSummary({ session, notice }: SessionSummaryProps) {
  const details = [
    { label: 'Name', value: session.name },
    { label: 'Project', value: session.project_name },
    { label: 'Grid', value: session.grid_name },
    { label: 'Session Plan', value: session.session_plan_name },
    ...(session.magnification_display ? [{ label: 'Magnification', value: session.magnification_display }] : []),
    ...(session.acquisition
      ? [
          { label: 'Super-resolution', value: session.acquisition.super_resolution ? 'Yes' : 'No' },
          { label: 'Phase plate used', value: usageLabel(session.acquisition.phase_plate_used) },
          { label: 'Energy filter used', value: usageLabel(session.acquisition.energy_filter_used) },
        ]
      : []),
  ];

  const paths = [
    { label: 'Frames', path: session.frames },
    { label: 'Sums', path: session.sums },
    { label: 'Mdocs', path: session.mdocs },
    { label: 'Parents', path: session.parents },
    { label: 'Atlas', path: session.atlas },
  ];

  const hasAnyPath = paths.some((p) => p.path?.directory);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {details.map((d) => (
        <Box key={d.label} sx={{ display: 'flex', gap: 1 }}>
          <Typography variant="body1" color="text.secondary" sx={{ minWidth: 130, fontWeight: 600 }}>
            {d.label}:
          </Typography>
          <Typography variant="body1">{d.value ?? '—'}</Typography>
        </Box>
      ))}

      {hasAnyPath && (
        <>
          {notice}
          <Box sx={{ mt: 1 }}>
            {paths.map((p) => (
              <PathRow key={p.label} label={p.label} path={p.path} />
            ))}
          </Box>
        </>
      )}
    </Box>
  );
}
