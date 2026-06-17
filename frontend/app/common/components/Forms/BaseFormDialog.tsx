'use client';

import React from 'react';
import { Box, CircularProgress } from '@mui/material';
import { Button, Dialog, DialogContent, DialogTitle, Icon } from '@czi-sds/components';
import { DialogTitle as MuiDialogTitle, IconButton, Typography } from '@mui/material';

interface BaseFormDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  titleExtra?: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  onSave: () => void;
  isSubmitting?: boolean;
  saveButtonText?: string;
  disabled?: boolean;
}

export const BaseFormDialog: React.FC<BaseFormDialogProps> = ({
  open,
  onClose,
  title,
  titleExtra,
  subtitle,
  children,
  onSave,
  isSubmitting = false,
  saveButtonText = 'Save',
  disabled = false,
}) => {
  return (
    <Dialog onClose={onClose} open={open} sdsSize="xs">
      {titleExtra ? (
        <MuiDialogTitle
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            p: 3,
            pb: 2,
          }}
        >
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h3" component="div" sx={{ fontWeight: 600 }}>
                {title}
              </Typography>
              {titleExtra}
            </Box>
            {Boolean(subtitle) && (
              <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <IconButton onClick={onClose} size="small" sx={{ mt: -0.5, mr: -1 }}>
            <Icon sdsIcon="XMark" sdsSize="l" color="gray" />
          </IconButton>
        </MuiDialogTitle>
      ) : (
        <DialogTitle title={title} subtitle={subtitle as string | undefined} onClose={onClose} />
      )}
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, pt: 2, pb: 2, mt: 2 }}>
          {children}

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button sdsType="secondary" sdsStyle="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              sdsType="primary"
              sdsStyle="solid"
              onClick={onSave}
              disabled={isSubmitting || disabled}
              startIcon={isSubmitting ? <CircularProgress size={16} /> : undefined}
            >
              {isSubmitting ? 'Saving...' : saveButtonText}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
