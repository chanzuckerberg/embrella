'use client';

import React, { useState } from 'react';
import { Box, TextField, Alert } from '@mui/material';
import { BaseFormDialog } from '@app/common/components/Forms/BaseFormDialog';
import { disabledTextFieldStyles } from '@app/components/GridsLogging/GridBox/DisableBoxStyle';
import { useCreateExternalResource } from '@app/common/hooks/useGridLogging';
import type { ExternalResource } from '@app/common/types/gridLogging/externalResource';
import { detectDocumentationSystemFromUrl } from '@app/common/utils/documentationUrl';

export const CreateNotesPageDialog: React.FC<{
  open: boolean;
  onClose: () => void;
  onSave: (resource: ExternalResource) => void;
}> = ({ open, onClose, onSave }) => {
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const { createExternalResource, isCreating, error, clearError } = useCreateExternalResource();

  // Reset the form when the dialog opens.
  const [wasOpen, setWasOpen] = useState(open);
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setName('');
      setUrl('');
      clearError();
    }
  }

  const handleSave = async () => {
    if (!name.trim() || !url.trim()) {
      return;
    }
    const trimmedUrl = url.trim();
    const result = await createExternalResource({
      resource_type: 'doc_page',
      system_name: detectDocumentationSystemFromUrl(trimmedUrl),
      name: name.trim(),
      url: trimmedUrl,
    });
    if (result?.resource) {
      onSave(result.resource);
      onClose();
    }
  };

  const isFormValid = Boolean(name.trim() && url.trim());

  return (
    <BaseFormDialog
      open={open}
      onClose={onClose}
      title="Create a Notes Page"
      onSave={handleSave}
      isSubmitting={isCreating}
      disabled={!isFormValid}
    >
      {Boolean(error) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField
          required
          label="Name"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          sx={{ ...disabledTextFieldStyles, flex: 1 }}
        />
        <TextField
          required
          label="Url"
          placeholder="Url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          sx={{ ...disabledTextFieldStyles, flex: 1 }}
        />
      </Box>
    </BaseFormDialog>
  );
};
