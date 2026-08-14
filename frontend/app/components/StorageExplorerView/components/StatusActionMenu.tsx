import { useState } from 'react';
import { ListItemIcon, ListItemText, Menu, MenuItem, Typography } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DeleteIcon from '@mui/icons-material/Delete';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import UndoIcon from '@mui/icons-material/Undo';

import { STATUS_LABELS } from '@app/components/DirectoryExplorerView/types';

import { DecisionTarget, SettableStatus } from '../types';

const CHOICES: SettableStatus[] = ['preserve', 'delete', 'review', 'unset'];

/** Same icons and colours as the All Paths tab's action menu. */
const STATUS_ICONS: Record<SettableStatus, React.ReactNode> = {
  preserve: <CheckCircleIcon fontSize="small" sx={{ color: '#4caf50' }} />,
  delete: <DeleteIcon fontSize="small" sx={{ color: '#f44336' }} />,
  review: <HelpOutlineIcon fontSize="small" sx={{ color: '#ff9800' }} />,
  unset: <UndoIcon fontSize="small" sx={{ color: '#9e9e9e' }} />,
};

interface StatusActionMenuProps {
  anchor: HTMLElement | null;
  target: DecisionTarget | null;
  onClose: () => void;
  onChoose: (status: SettableStatus, notes: string) => Promise<void>;
}

/**
 * The set-status menu, shared by all three tiers.
 */
export const StatusActionMenu = ({ anchor, target, onClose, onChoose }: StatusActionMenuProps) => {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    setError(null);
    onClose();
  };

  const handleSelect = async (status: SettableStatus) => {
    if (status === target?.status) {
      close();
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onChoose(status, '');
      close();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record the decision');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Menu
      anchorEl={anchor}
      open={Boolean(anchor)}
      onClose={close}
      // This app scrolls inside TableWrapper, not on body, so MUI's scroll lock
      // has no scrollbar to compensate for and its padding shifts the whole
      // table sideways when the menu opens.
      disableScrollLock
    >
      {!!target?.inheritedFrom && (
        // Says why the row reads what it reads, without restating the path --
        // that is on the tag's own tooltip, and at ~90 characters it wrapped to
        // three lines and dwarfed the four options underneath it.
        <MenuItem disabled sx={{ opacity: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Inherited from the tier above
          </Typography>
        </MenuItem>
      )}

      {CHOICES.map((status) => (
        <MenuItem
          key={status}
          onClick={() => void handleSelect(status)}
          selected={status === target?.status}
          disabled={saving}
        >
          <ListItemIcon>{STATUS_ICONS[status]}</ListItemIcon>
          <ListItemText>{STATUS_LABELS[status]}</ListItemText>
        </MenuItem>
      ))}

      {!!error && (
        <MenuItem disabled sx={{ opacity: 1, maxWidth: 320, whiteSpace: 'normal' }}>
          <Typography variant="caption" color="error">
            {error}
          </Typography>
        </MenuItem>
      )}
    </Menu>
  );
};
