'use client';

import React, { useEffect, useRef } from 'react';
import { Box, ButtonBase } from '@mui/material';
import { DragDropProvider, DragEndEvent } from '@dnd-kit/react';
import { useSortable } from '@dnd-kit/react/sortable';
import { move } from '@dnd-kit/helpers';
import { imageSrc } from '@app/common/queries/imagesApi';
import { ImageAsset, ImageRendition } from '@app/common/types/images';
import { THUMB_TILE_PX } from './constants';

interface ImageThumbStripProps {
  images: ImageAsset[];
  onSelect: (index: number) => void;
  selectedIndex?: number;
  // Drag thumbs to reorder; called with every image id in the new order. Absent → no dragging.
  onReorder?: (imageIds: string[]) => void;
}

/**
 * Row of square thumbnails, scrolling sideways when it overflows.
 * Drag (or focus + Space, arrows, Space) to reorder; a plain click still selects.
 */
export const ImageThumbStrip: React.FC<ImageThumbStripProps> = ({ images, onSelect, selectedIndex, onReorder }) => {
  // dnd-kit already moved the DOM; report the new order unless the drop was cancelled or a no-op
  const handleDragEnd = (event: DragEndEvent) => {
    if (!onReorder || event.canceled) return;

    const ids = images.map((image) => image.id);
    const reordered = move(ids, event);
    if (reordered.every((id, index) => id === ids[index])) return;

    onReorder(reordered);
  };

  return (
    <DragDropProvider onDragEnd={handleDragEnd}>
      <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', py: 0.5 }}>
        {images.map((image, index) => (
          <SortableThumb
            key={image.id}
            image={image}
            index={index}
            isSelected={index === selectedIndex}
            isSortable={onReorder !== undefined}
            onSelect={onSelect}
          />
        ))}
      </Box>
    </DragDropProvider>
  );
};

interface SortableThumbProps {
  image: ImageAsset;
  index: number;
  isSelected: boolean;
  isSortable: boolean;
  onSelect: (index: number) => void;
}

const SortableThumb: React.FC<SortableThumbProps> = ({ image, index, isSelected, isSortable, onSelect }) => {
  const elementRef = useRef<HTMLButtonElement | null>(null);
  const { ref: sortableRef, isDragging } = useSortable({ id: image.id, index, disabled: !isSortable });

  // Keep the selected tile visible as the carousel moves
  useEffect(() => {
    if (isSelected) elementRef.current?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
  }, [isSelected]);

  return (
    <ButtonBase
      ref={(element: HTMLButtonElement | null) => {
        elementRef.current = element;
        sortableRef(element);
      }}
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
        cursor: isSortable ? 'grab' : 'pointer',
        boxShadow: isDragging ? 4 : 'none',
      }}
    >
      <Box
        component="img"
        src={imageSrc(image, ImageRendition.THUMB)}
        alt={image.original_name}
        loading="lazy"
        draggable={false}
        sx={{ width: '100%', height: '100%', objectFit: 'cover' }}
      />
    </ButtonBase>
  );
};
