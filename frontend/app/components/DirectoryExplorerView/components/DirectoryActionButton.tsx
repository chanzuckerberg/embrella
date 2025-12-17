import { useState } from 'react';
import { IconButton, Menu, MenuItem, ListItemIcon, ListItemText, CircularProgress } from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DeleteIcon from '@mui/icons-material/Delete';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import UndoIcon from '@mui/icons-material/Undo';

import { PreserveStatus, STATUS_LABELS } from '../types';
import { updateDirectoryStatus } from '../api';

interface DirectoryActionButtonProps {
  directoryId: number;
  currentStatus: PreserveStatus;
  onActionComplete: () => void;
  disabled?: boolean;
}

const STATUS_ICONS: Record<PreserveStatus, React.ReactNode> = {
  preserve: <CheckCircleIcon fontSize="small" sx={{ color: '#4caf50' }} />,
  delete: <DeleteIcon fontSize="small" sx={{ color: '#f44336' }} />,
  review: <HelpOutlineIcon fontSize="small" sx={{ color: '#ff9800' }} />,
  unset: <UndoIcon fontSize="small" sx={{ color: '#9e9e9e' }} />,
};

/**
 * Action button with dropdown menu for changing directory preservation status.
 */
export const DirectoryActionButton = ({
  directoryId,
  currentStatus,
  onActionComplete,
  disabled = false,
}: DirectoryActionButtonProps) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [loading, setLoading] = useState(false);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleStatusChange = async (newStatus: PreserveStatus) => {
    if (newStatus === currentStatus) {
      handleClose();
      return;
    }

    setLoading(true);
    try {
      await updateDirectoryStatus(directoryId, newStatus);
      onActionComplete();
    } catch (error) {
      console.error('Failed to update directory status:', error);
    } finally {
      setLoading(false);
      handleClose();
    }
  };

  const statusOptions: PreserveStatus[] = ['preserve', 'delete', 'review', 'unset'];

  return (
    <>
      <IconButton
        size="small"
        onClick={handleClick}
        aria-label="Directory actions"
        aria-controls={open ? 'directory-actions-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        disabled={loading || disabled}
        sx={disabled ? { opacity: 0.3 } : undefined}
      >
        {loading ? <CircularProgress size={20} /> : <MoreVertIcon />}
      </IconButton>
      <Menu
        id="directory-actions-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'directory-actions-button',
        }}
      >
        {statusOptions.map((status) => (
          <MenuItem key={status} onClick={() => handleStatusChange(status)} selected={status === currentStatus}>
            <ListItemIcon>{STATUS_ICONS[status]}</ListItemIcon>
            <ListItemText>{STATUS_LABELS[status]}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};
