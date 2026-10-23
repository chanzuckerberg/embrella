'use client';

import React, { useEffect, useRef } from 'react';
import { Box, ButtonBase } from '@mui/material';
import { imageSrc } from '@app/common/queries/imagesApi';
import { ImageAsset, ImageRendition } from '@app/common/types/images';
import { THUMB_TILE_PX } from './constants';

interface ImageThumbStripProps {
  images: ImageAsset[];
  onSelect: (index: number) => void;
  selectedIndex?: number;
}

/** Row of square thumbnails, scrolling sideways when it overflows. */
export const ImageThumbStrip: React.FC<ImageThumbStripProps> = ({ images, onSelect, selectedIndex }) => {
  const selectedRef = useRef<HTMLButtonElement>(null);

  // Keep the selected tile visible as the carousel moves
  useEffect(() => {
    selectedRef.current?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
  }, [selectedIndex]);

  return (
    <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', py: 0.5 }}>
      {images.map((image, index) => {
        const isSelected = index === selectedIndex;
        return (
          <ButtonBase
            key={image.id}
            ref={isSelected ? selectedRef : undefined}
            onClick={() => onSelect(index)}
            aria-label={`Show ${image.original_name}`}
            aria-current={isSelected || undefined}
            sx={{
              flex: '0 0 auto',
              width: THUMB_TILE_PX,
              height: THUMB_TILE_PX,
              borderRadius: 1,
              overflow: 'hidden',
              outline: isSelected ? '2px solid' : 'none',
              outlineColor: 'primary.main',
              outlineOffset: 1,
            }}
          >
            <Box
              component="img"
              src={imageSrc(image, ImageRendition.THUMB)}
              alt={image.original_name}
              loading="lazy"
              sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </ButtonBase>
        );
      })}
    </Box>
  );
};
