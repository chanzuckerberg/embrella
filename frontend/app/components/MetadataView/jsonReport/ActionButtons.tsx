import React from 'react';
import { FormControlLabel, Switch, IconButton } from '@mui/material';
import { Icon } from '@czi-sds/components';

interface ActionButtonsProps {
  sortEnabled: boolean;
  onSortToggle: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onCopy: () => void;
  onDownload: () => void;
  onClose: () => void;
}

/**
 * Component for rendering action buttons in the RawJson header
 */
export const ActionButtons: React.FC<ActionButtonsProps> = React.memo(
  ({ sortEnabled, onSortToggle, onCopy, onDownload, onClose }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <FormControlLabel
        control={<Switch checked={sortEnabled} onChange={onSortToggle} color="primary" size="small" />}
        label="Sort"
        sx={{ marginRight: 0 }}
      />
      <IconButton size="small" onClick={onCopy} title="Copy JSON" sx={{ padding: '4px' }}>
        <Icon color="green" sdsIcon="Copy" sdsSize="s" />
      </IconButton>
      <IconButton size="small" onClick={onDownload} title="Download JSON" sx={{ padding: '4px' }}>
        <Icon color="green" sdsIcon="Download" sdsSize="s" />
      </IconButton>
      <IconButton size="small" onClick={onClose} title="Close" sx={{ padding: '4px' }}>
        <Icon color="green" sdsIcon="XMark" sdsSize="s" />
      </IconButton>
    </div>
  )
);

ActionButtons.displayName = 'ActionButtons';
