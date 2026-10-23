'use client';

import React from 'react';
import { Alert, Box, CircularProgress, Typography } from '@mui/material';
import { ImageGallery, PasteMode } from '@app/common/components/images';
import {
  useDeleteGridImage,
  useGridImageUploads,
  useGridImages,
  useUpdateImageNotes,
} from '@app/common/hooks/images/useGridImages';

interface ImagesTabProps {
  gridId: number;
  imageId: string | null;
  onImageChange: (imageId: string) => void;
}

// Mounted only while the tab is active: leaving it keeps queued files uploading, unseen
export const ImagesTab: React.FC<ImagesTabProps> = ({ gridId, imageId, onImageChange }) => {
  const { data: images, isLoading, isError } = useGridImages(gridId);
  const { uploads, add, reject, dismiss } = useGridImageUploads(gridId);
  const updateNotes = useUpdateImageNotes(gridId);
  const deleteImage = useDeleteGridImage(gridId);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (isError || !images) {
    return (
      <Typography variant="body2" color="error">
        Could not load images.
      </Typography>
    );
  }

  return (
    <>
      {updateNotes.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Notes not saved: {updateNotes.error.message}
        </Alert>
      )}

      <ImageGallery
        images={images}
        uploads={uploads}
        onFiles={add}
        onRejected={reject}
        onDismissUpload={dismiss}
        onNotesChange={(image, notes) => updateNotes.mutateAsync({ imageId: image.id, notes })}
        onDelete={(image) => deleteImage.mutateAsync(image.id)}
        paste={PasteMode.DOCUMENT}
        initialIndex={Math.max(
          images.findIndex((image) => image.id === imageId),
          0
        )}
        onSelectedChange={onImageChange}
      />
    </>
  );
};
