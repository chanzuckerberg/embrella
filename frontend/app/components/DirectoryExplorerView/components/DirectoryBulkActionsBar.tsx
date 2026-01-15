import { useState } from 'react';
import { Box, Button, ButtonGroup, Typography, CircularProgress, Snackbar, Alert } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DeleteIcon from '@mui/icons-material/Delete';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import UndoIcon from '@mui/icons-material/Undo';

import { PreserveStatus, STATUS_LABELS } from '../types';
import { bulkUpdateDirectoryStatus } from '../api';

interface DirectoryBulkActionsBarProps {
  selectedIds: number[];
  onActionComplete: () => void;
  onClearSelection: () => void;
}

const STATUS_BUTTONS: Array<{
  status: PreserveStatus;
  icon: React.ReactNode;
  color: 'success' | 'error' | 'warning' | 'inherit';
}> = [
  { status: 'preserve', icon: <CheckCircleIcon />, color: 'success' },
  { status: 'delete', icon: <DeleteIcon />, color: 'error' },
  { status: 'review', icon: <HelpOutlineIcon />, color: 'warning' },
  { status: 'unset', icon: <UndoIcon />, color: 'inherit' },
];

/**
 * Floating action bar for bulk status updates when rows are selected.
 */
export const DirectoryBulkActionsBar = ({
  selectedIds,
  onActionComplete,
  onClearSelection,
}: DirectoryBulkActionsBarProps) => {
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({ open: false, message: '', severity: 'success' });

  if (selectedIds.length === 0) {
    return null;
  }

  const handleBulkUpdate = async (status: PreserveStatus) => {
    setLoading(true);
    try {
      const result = await bulkUpdateDirectoryStatus(selectedIds, status);
      setSnackbar({
        open: true,
        message: `Updated ${result.updated} directories to "${STATUS_LABELS[status]}"`,
        severity: 'success',
      });
      onActionComplete();
      onClearSelection();
    } catch (error) {
      setSnackbar({
        open: true,
        message: error instanceof Error ? error.message : 'Failed to update directories',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  return (
    <>
      <Box
        sx={{
          position: 'sticky',
          bottom: 16,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          zIndex: 10,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            px: 3,
            py: 1.5,
            backgroundColor: 'background.paper',
            borderRadius: 2,
            boxShadow: 3,
            border: 1,
            borderColor: 'divider',
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {selectedIds.length} selected
          </Typography>

          <ButtonGroup variant="outlined" size="small" disabled={loading}>
            {STATUS_BUTTONS.map(({ status, icon, color }) => (
              <Button key={status} onClick={() => handleBulkUpdate(status)} startIcon={icon} color={color}>
                {STATUS_LABELS[status]}
              </Button>
            ))}
          </ButtonGroup>

          <Button variant="text" size="small" onClick={onClearSelection} disabled={loading}>
            Clear
          </Button>

          {loading && <CircularProgress size={20} />}
        </Box>
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
};
