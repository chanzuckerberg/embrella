'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Box } from '@mui/material';
import { ConfirmDialog } from '@app/common/components/Forms/ConfirmDialog';
import { ImageAsset, UploadItem } from '@app/common/types/images';
import { ImageCarousel } from './ImageCarousel';
import { ImageUploader, UploaderSize } from './ImageUploader';
import { ImageViewer } from './ImageViewer';
import { PasteMode } from './usePasteImages';

interface ImageGalleryProps {
  images: ImageAsset[];
  uploads: UploadItem[];
  onFiles: (files: File[]) => void;
  onRejected: (file: File, message: string) => void;
  onDismissUpload: (key: string) => void;
  onNotesChange: (image: ImageAsset, notes: string) => Promise<unknown>;
  onDelete: (image: ImageAsset) => Promise<void>;
  onReorder: (imageIds: string[]) => void;
  paste: PasteMode;
  initialIndex?: number;
  onSelectedChange?: (imageId: string) => void;
}

/**
 * Owner-agnostic image gallery: carousel, fullscreen viewer, uploader and delete confirm.
 * Data comes from the caller, e.g. a grid's hooks, so other owners can reuse it.
 */
export const ImageGallery: React.FC<ImageGalleryProps> = ({
  images,
  uploads,
  onFiles,
  onRejected,
  onDismissUpload,
  onNotesChange,
  onDelete,
  onReorder,
  paste,
  initialIndex = 0,
  onSelectedChange,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(initialIndex);
  const [viewerIndex, setViewerIndex] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ImageAsset | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Jump to a newly uploaded image, which arrives last
  const previousCount = useRef(images.length);
  useEffect(() => {
    if (images.length > previousCount.current) {
      setSelectedIndex(images.length - 1);
    }
    previousCount.current = images.length;
  }, [images.length]);

  // Stay in range after a delete
  const shownIndex = Math.min(selectedIndex, Math.max(images.length - 1, 0));

  // Report the shown image, e.g. so the caller can keep it in the URL
  const shownId = images[shownIndex]?.id;
  useEffect(() => {
    if (shownId) onSelectedChange?.(shownId);
  }, [shownId, onSelectedChange]);

  // Selection follows the shown image to its new position
  const reorder = (imageIds: string[]) => {
    if (shownId) setSelectedIndex(imageIds.indexOf(shownId));
    onReorder(imageIds);
  };

  const closeDelete = () => {
    setPendingDelete(null);
    setDeleteError(null);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;

    setIsDeleting(true);
    try {
      await onDelete(pendingDelete);
      closeDelete();
    } catch (error) {
      setDeleteError((error as Error).message);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {images.length > 0 && (
        <ImageCarousel
          images={images}
          selectedIndex={shownIndex}
          onSelect={setSelectedIndex}
          onOpen={setViewerIndex}
          onNotesChange={onNotesChange}
          onDelete={setPendingDelete}
          onReorder={reorder}
        />
      )}

      <ImageUploader
        uploads={uploads}
        onFiles={onFiles}
        onRejected={onRejected}
        onDismiss={onDismissUpload}
        size={UploaderSize.FULL}
        paste={paste}
      />

      <ImageViewer
        images={images}
        index={viewerIndex}
        onIndexChange={(index) => {
          setViewerIndex(index);
          setSelectedIndex(index);
        }}
        onClose={() => setViewerIndex(null)}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        onClose={closeDelete}
        onConfirm={confirmDelete}
        title="Delete this image?"
        heading={pendingDelete?.original_name ?? ''}
        body="The image and its notes will be removed. This cannot be undone."
        confirmText="Delete"
        submittingText="Deleting…"
        cancelText="Cancel"
        isSubmitting={isDeleting}
        error={deleteError}
      />
    </Box>
  );
};
