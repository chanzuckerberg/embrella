'use client';

import { Alert } from '@mui/material';

export function ReadOnlyNotice({ nonOwner }: { nonOwner: boolean }) {
  return (
    <Alert severity="info" sx={{ mb: 3 }}>
      {nonOwner
        ? "You're viewing another user's submission - it's read-only."
        : 'Metadata is read-only once preparation has started.'}
    </Alert>
  );
}
