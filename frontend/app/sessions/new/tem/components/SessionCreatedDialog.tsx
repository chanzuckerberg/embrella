'use client';

import React from 'react';
import { Alert, Box, Typography } from '@mui/material';
import { Button, Dialog, DialogActions, DialogContent, DialogTitle } from '@czi-sds/components';
import { CreatedSession, RolePath } from '../types';

interface SessionCreatedDialogProps {
  open: boolean;
  session: CreatedSession | null;
  onCreateAnother: () => void;
  onDone: () => void;
}

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

export function SessionCreatedDialog({ open, session, onCreateAnother, onDone }: SessionCreatedDialogProps) {
  if (!session) return null;

  const details = [
    { label: 'Name', value: session.name },
    { label: 'Project', value: session.project_name },
    { label: 'Grid', value: session.grid_name },
    { label: 'Session Plan', value: session.session_plan_name },
    ...(session.magnification_display ? [{ label: 'Magnification', value: session.magnification_display }] : []),
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
    <Dialog open={open} onClose={onDone} sdsSize="s">
      <DialogTitle title="Session Created" onClose={onDone} />
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {details.map((d) => (
            <Box key={d.label} sx={{ display: 'flex', gap: 1 }}>
              <Typography variant="body2" color="text.secondary" sx={{ minWidth: 120, fontWeight: 600 }}>
                {d.label}:
              </Typography>
              <Typography variant="body2">{d.value}</Typography>
            </Box>
          ))}

          {hasAnyPath && (
            <>
              <Alert severity="info" sx={{ mt: 1 }}>
                Please review the file directories below and ensure data is stored correctly.
              </Alert>
              <Box sx={{ mt: 1 }}>
                {paths.map((p) => (
                  <PathRow key={p.label} label={p.label} path={p.path} />
                ))}
              </Box>
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button sdsType="secondary" sdsStyle="outline" onClick={onCreateAnother}>
          Create Another
        </Button>
        <Button sdsType="secondary" sdsStyle="outline" onClick={() => window.open(session.legacy_url, '_blank')}>
          View Details
        </Button>
        <Button sdsType="primary" sdsStyle="solid" onClick={onDone}>
          Done
        </Button>
      </DialogActions>
    </Dialog>
  );
}
