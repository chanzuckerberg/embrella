'use client';

import React, { useEffect, useRef, useState } from 'react';
import useEmblaCarousel from 'embla-carousel-react';
import { Box, Fade, IconButton, TextField, Tooltip, Typography } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { imageSrc } from '@app/common/queries/imagesApi';
import { ImageAsset, ImageRendition } from '@app/common/types/images';
import { PREVIEW_HEIGHT_PX } from './constants';
import { ImageThumbStrip } from './ImageThumbStrip';

interface ImageCarouselProps {
  images: ImageAsset[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onOpen: (index: number) => void;
  onNotesChange: (image: ImageAsset, notes: string) => Promise<unknown>;
  onDelete: (image: ImageAsset) => void;
}

/**
 * Swipeable previews with a thumbnail row, details, actions and notes for the shown image.
 *
 *   ┌──────────── preview (swipe / ‹ › ) ────────────┐   click → fullscreen viewer
 *   └─────────────────────────────────────────────────┘
 *   name · size · who · when                 ⬇  🗑
 *   [▣][▣][▣]   thumbs
 *   Notes: [ … ]  saves on blur
 */
export const ImageCarousel: React.FC<ImageCarouselProps> = ({
  images,
  selectedIndex,
  onSelect,
  onOpen,
  onNotesChange,
  onDelete,
}) => {
  const [emblaRef, emblaApi] = useEmblaCarousel();

  // Swipes report back to the parent's selection
  useEffect(() => {
    if (!emblaApi) return;

    const handleSelect = () => onSelect(emblaApi.selectedScrollSnap());
    emblaApi.on('select', handleSelect);
    return () => {
      emblaApi.off('select', handleSelect);
    };
  }, [emblaApi, onSelect]);

  // Thumb clicks and new uploads move the carousel
  useEffect(() => {
    if (emblaApi && emblaApi.selectedScrollSnap() !== selectedIndex) {
      emblaApi.scrollTo(selectedIndex);
    }
  }, [emblaApi, selectedIndex, images.length]);

  const image = images[selectedIndex];
  if (!image) return null;

  return (
    <Box>
      <Box sx={{ position: 'relative' }}>
        <Box ref={emblaRef} sx={{ overflow: 'hidden', borderRadius: 1, bgcolor: 'grey.100' }}>
          <Box sx={{ display: 'flex' }}>
            {images.map((slide, index) => (
              <Box
                key={slide.id}
                sx={{
                  flex: '0 0 100%',
                  minWidth: 0,
                  height: PREVIEW_HEIGHT_PX,
                  display: 'flex',
                  justifyContent: 'center',
                }}
              >
                {/* Neighbours only: originals are never loaded, and far slides load when reached */}
                {Math.abs(index - selectedIndex) <= 1 && (
                  <Box
                    component="img"
                    src={imageSrc(slide, ImageRendition.PREVIEW)}
                    alt={slide.original_name}
                    onClick={() => onOpen(index)}
                    sx={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', cursor: 'zoom-in' }}
                  />
                )}
              </Box>
            ))}
          </Box>
        </Box>

        {images.length > 1 && (
          <>
            <SlideButton side="left" disabled={selectedIndex === 0} onClick={() => onSelect(selectedIndex - 1)} />
            <SlideButton
              side="right"
              disabled={selectedIndex === images.length - 1}
              onClick={() => onSelect(selectedIndex + 1)}
            />
          </>
        )}
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
        <Typography variant="body2" noWrap sx={{ flex: 1, minWidth: 0 }} title={image.original_name}>
          {image.original_name}
          <Typography component="span" variant="caption" color="text.secondary">
            {' · '}
            {image.width} × {image.height}
            {image.uploaded_by && ` · ${image.uploaded_by}`}
            {' · '}
            {new Date(image.created_at).toLocaleDateString()}
          </Typography>
        </Typography>

        <Tooltip title="Download original">
          <IconButton
            size="small"
            component="a"
            href={imageSrc(image, ImageRendition.ORIGINAL)}
            aria-label="Download original"
          >
            <Icon sdsIcon="Download" sdsSize="s" color="gray" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Delete image">
          <IconButton size="small" onClick={() => onDelete(image)} aria-label="Delete image">
            <Icon sdsIcon="TrashCan" sdsSize="s" color="gray" />
          </IconButton>
        </Tooltip>
      </Box>

      {images.length > 1 && <ImageThumbStrip images={images} selectedIndex={selectedIndex} onSelect={onSelect} />}

      {/* Keyed by image so switching images resets the draft */}
      <NotesField key={image.id} image={image} onSave={(notes) => onNotesChange(image, notes)} />
    </Box>
  );
};

const SlideButton: React.FC<{ side: 'left' | 'right'; disabled: boolean; onClick: () => void }> = ({
  side,
  disabled,
  onClick,
}) => (
  <IconButton
    onClick={onClick}
    disabled={disabled}
    aria-label={side === 'left' ? 'Previous image' : 'Next image'}
    sx={{
      position: 'absolute',
      top: '50%',
      transform: 'translateY(-50%)',
      [side]: 8,
      bgcolor: 'background.paper',
      '&:hover': { bgcolor: 'background.paper' },
    }}
  >
    <Icon sdsIcon={side === 'left' ? 'ChevronLeft' : 'ChevronRight'} sdsSize="s" />
  </IconButton>
);

// "Saved" flash after notes save: quick fade in, short hold, slower fade out
const SAVED_HOLD_MS = 1000;
const SAVED_FADE_MS = { enter: 150, exit: 600 };

const NotesField: React.FC<{ image: ImageAsset; onSave: (notes: string) => Promise<unknown> }> = ({
  image,
  onSave,
}) => {
  const [draft, setDraft] = useState(image.notes);
  const [showSaved, setShowSaved] = useState(false);
  const latestDraft = useRef(image.notes);

  // Flash "Saved", then let it fade out on its own
  useEffect(() => {
    if (!showSaved) return;

    const timer = setTimeout(() => setShowSaved(false), SAVED_HOLD_MS);
    return () => clearTimeout(timer);
  }, [showSaved]);

  const save = async () => {
    if (draft === image.notes) return;

    const saving = draft;
    try {
      await onSave(saving);
      // Typed again while saving: the field holds unsaved text, so don't claim "Saved"
      setShowSaved(latestDraft.current === saving);
    } catch {
      // The caller shows the error; no "Saved"
    }
  };

  return (
    <TextField
      label="Notes"
      placeholder="e.g. square B4 cracked, ice looks thin"
      multiline
      minRows={2}
      fullWidth
      size="small"
      value={draft}
      onChange={(event) => {
        setDraft(event.target.value);
        latestDraft.current = event.target.value;
        setShowSaved(false);
      }}
      onBlur={save}
      // Helper line always renders, so "Saved" fading in and out never shifts the layout
      helperText={
        <Fade in={showSaved} timeout={SAVED_FADE_MS}>
          <span role="status">Saved</span>
        </Fade>
      }
      sx={{ mt: 1.5 }}
    />
  );
};
