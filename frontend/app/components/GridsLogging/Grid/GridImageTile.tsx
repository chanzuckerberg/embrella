'use client';

import React, { useContext, useState } from 'react';
import { useQueryState } from 'nuqs';
import { Box, ButtonBase, Typography } from '@mui/material';
import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { ImageUploader, PasteMode, UploaderSize } from '@app/common/components/images';
import { useGridImageUploads, useGridImages } from '@app/common/hooks/images/useGridImages';
import { imageSrc } from '@app/common/queries/imagesApi';
import { ImageRendition } from '@app/common/types/images';
import { GridDetailDialog } from '@app/components/GridDetailDialog/GridDetailDialog';

// Matches the grid icon above it
const TILE_PX = 150;

interface GridImageTileProps {
  gridId: number;
  onGridUpdated?: () => void;
}

/**
 * Under the grid icon in grid logging: the first image (opens the Images tab), or an
 * upload area while the grid has none or uploads are in flight.
 */
export const GridImageTile: React.FC<GridImageTileProps> = ({ gridId, onGridUpdated }) => {
  const imagesEnabled = useContext(FeatureFlagsContext).includes(FEATURE_FLAG.IMAGES);
  const { data: images = [] } = useGridImages(imagesEnabled ? gridId : null);
  const { uploads, add, reject, dismiss } = useGridImageUploads(gridId);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [, setGridTab] = useQueryState('gridTab');

  if (!imagesEnabled) return null;

  const openImages = () => {
    setGridTab('images');
    setDialogOpen(true);
  };

  const [first] = images;

  return (
    <Box sx={{ width: TILE_PX, mt: 1, ml: '7px' }}>
      {first && (
        <ButtonBase
          onClick={openImages}
          aria-label={`Open ${images.length} grid image${images.length > 1 ? 's' : ''}`}
          sx={{ position: 'relative', width: TILE_PX, height: TILE_PX, borderRadius: 1, overflow: 'hidden' }}
        >
          <Box
            component="img"
            src={imageSrc(first, ImageRendition.THUMB)}
            alt={first.original_name}
            sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
          {images.length > 1 && (
            <Typography
              variant="caption"
              sx={{
                position: 'absolute',
                right: 4,
                bottom: 4,
                px: 0.75,
                borderRadius: 1,
                color: 'common.white',
                bgcolor: 'rgba(0, 0, 0, 0.6)',
              }}
            >
              +{images.length - 1}
            </Typography>
          )}
        </ButtonBase>
      )}

      {(!first || uploads.length > 0) && (
        <Box sx={{ mt: first ? 1 : 0 }}>
          <ImageUploader
            uploads={uploads}
            onFiles={add}
            onRejected={reject}
            onDismiss={dismiss}
            size={UploaderSize.COMPACT}
            // The dialog's Images tab takes over paste while it's open
            paste={dialogOpen ? PasteMode.OFF : PasteMode.DOCUMENT}
          />
        </Box>
      )}

      <GridDetailDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        gridId={gridId}
        onGridUpdated={onGridUpdated}
      />
    </Box>
  );
};
