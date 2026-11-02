'use client';

import React, { useCallback } from 'react';
import { ErrorCode, FileRejection, useDropzone } from 'react-dropzone';
import AddPhotoIcon from '@mui/icons-material/AddPhotoAlternateOutlined';
import { Box, IconButton, LinearProgress, Typography } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { UploadItem, UploadStatus } from '@app/common/types/images';
import { ACCEPTED_IMAGE_TYPES, MAX_UPLOAD_BYTES, TOO_LARGE_MESSAGE, WRONG_TYPE_MESSAGE } from './constants';
import { PasteMode, usePasteImages } from './usePasteImages';

export enum UploaderSize {
  FULL = 'full', // Wide drop area with instructions, e.g. under the carousel
  COMPACT = 'compact', // Small tile, e.g. under the grid icon in grid logging
}

interface ImageUploaderProps {
  uploads: UploadItem[];
  onFiles: (files: File[]) => void;
  onRejected: (file: File, message: string) => void;
  onDismiss: (key: string) => void;
  size: UploaderSize;
  paste: PasteMode;
}

const ACCEPTED_EXTENSIONS = Object.values(ACCEPTED_IMAGE_TYPES).flat();

// Upload icon size per uploader size
const ICON_PX = { [UploaderSize.FULL]: 32, [UploaderSize.COMPACT]: 24 };

/** Drop, browse or paste images. Shows each queued, uploading or failed file below. */
export const ImageUploader: React.FC<ImageUploaderProps> = ({
  uploads,
  onFiles,
  onRejected,
  onDismiss,
  size,
  paste,
}) => {
  const onDrop = useCallback(
    (accepted: File[], rejections: FileRejection[]) => {
      rejections.forEach(({ file, errors }) => onRejected(file, dropzoneMessage(errors[0]?.code)));
      if (accepted.length) {
        onFiles(accepted);
      }
    },
    [onFiles, onRejected]
  );

  // Pasted files skip react-dropzone, so apply the same checks here
  const onPaste = useCallback(
    (files: File[]) => {
      const accepted = files.filter((file) => {
        const message = clientRejection(file);
        if (message) {
          onRejected(file, message);
        }
        return !message;
      });
      if (accepted.length) {
        onFiles(accepted);
      }
    },
    [onFiles, onRejected]
  );
  usePasteImages(onPaste, paste);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPTED_IMAGE_TYPES,
    maxSize: MAX_UPLOAD_BYTES,
    onDrop,
  });

  const isCompact = size === UploaderSize.COMPACT;

  return (
    <Box>
      <Box
        {...getRootProps()}
        data-testid="image-dropzone"
        sx={{
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          borderRadius: 1,
          bgcolor: isDragActive ? 'action.hover' : 'transparent',
          cursor: 'pointer',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 0.5,
          textAlign: 'center',
          px: 2,
          py: isCompact ? 1.5 : 2,
          '&:hover': { borderColor: 'primary.main' },
        }}
      >
        <input {...getInputProps()} aria-label="Upload images" />
        <AddPhotoIcon sx={{ fontSize: ICON_PX[size], color: 'text.secondary' }} />
        <Typography variant={isCompact ? 'caption' : 'body2'}>
          {isDragActive ? 'Drop to upload' : 'Upload images'}
        </Typography>
        {!isCompact && (
          <Typography variant="caption" color="text.secondary">
            Drop, paste or click to browse
          </Typography>
        )}
      </Box>

      {uploads.map((item) => (
        <UploadRow key={item.key} item={item} onDismiss={onDismiss} />
      ))}
    </Box>
  );
};

const UploadRow: React.FC<{ item: UploadItem; onDismiss: (key: string) => void }> = ({ item, onDismiss }) => (
  <Box sx={{ mt: 1 }}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Typography variant="caption" noWrap sx={{ flex: 1, minWidth: 0 }}>
        {item.file.name}
      </Typography>

      {item.status === UploadStatus.QUEUED && (
        <Typography variant="caption" color="text.secondary">
          Waiting…
        </Typography>
      )}

      {item.status === UploadStatus.FAILED && (
        <IconButton size="small" aria-label={`Dismiss ${item.file.name}`} onClick={() => onDismiss(item.key)}>
          <Icon sdsIcon="XMark" sdsSize="xs" />
        </IconButton>
      )}
    </Box>

    {item.status === UploadStatus.UPLOADING && (
      <LinearProgress variant="determinate" value={Math.round(item.progress * 100)} />
    )}

    {item.status === UploadStatus.FAILED && (
      <Typography variant="caption" color="error" component="p">
        {item.error}
      </Typography>
    )}
  </Box>
);

function dropzoneMessage(code: string | undefined): string {
  if (code === ErrorCode.FileTooLarge) return TOO_LARGE_MESSAGE;
  return WRONG_TYPE_MESSAGE;
}

/** Same checks react-dropzone applies to dropped files, or null if fine. */
export function clientRejection(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  const isAccepted = file.type in ACCEPTED_IMAGE_TYPES || ACCEPTED_EXTENSIONS.includes(extension);

  if (!isAccepted) return WRONG_TYPE_MESSAGE;
  if (file.size > MAX_UPLOAD_BYTES) return TOO_LARGE_MESSAGE;
  return null;
}
