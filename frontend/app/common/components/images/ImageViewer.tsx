'use client';

import React, { useId } from 'react';
import { TransformComponent, TransformWrapper } from 'react-zoom-pan-pinch';
import ZoomOutMapIcon from '@mui/icons-material/ZoomOutMap';
import { Box, Dialog, IconButton, Tooltip, Typography } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { gray100, gray800 } from '@app/common/theme';
import { imageSrc } from '@app/common/queries/imagesApi';
import { ImageAsset, ImageRendition } from '@app/common/types/images';

// Wheel/pinch zoom range relative to fit-to-screen; the preview is ≤4096 px
const MAX_ZOOM = 8;

// SDS gray shade for text and icons on the dark viewer; the background is gray 800
const FOREGROUND_SHADE = 100;

// Matches SDS `sdsSize="s"` icons beside it
const ICON_PX = 16;

interface ImageViewerProps {
  images: ImageAsset[];
  index: number | null; // null = closed
  onIndexChange: (index: number) => void;
  onClose: () => void;
}

/**
 * Fullscreen zoom/pan of an image's preview, for quick screening. Arrow keys switch
 * images, Esc closes. Detailed viewing belongs to a dedicated viewer.
 */
export const ImageViewer: React.FC<ImageViewerProps> = ({ images, index, onIndexChange, onClose }) => {
  const titleId = useId();
  const image = index === null ? undefined : images[index];
  if (index === null || !image) return null;

  const hasPrevious = index > 0;
  const hasNext = index < images.length - 1;

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowLeft' && hasPrevious) onIndexChange(index - 1);
    if (event.key === 'ArrowRight' && hasNext) onIndexChange(index + 1);
  };

  return (
    <Dialog
      open
      fullScreen
      onClose={onClose}
      onKeyDown={handleKeyDown}
      aria-labelledby={titleId}
      PaperProps={{ sx: { bgcolor: (theme) => gray800({ theme }), color: (theme) => gray100({ theme }) } }}
    >
      {/* Keyed by image so each one opens unzoomed */}
      <TransformWrapper key={image.id} maxScale={MAX_ZOOM} centerOnInit>
        {({ zoomIn, zoomOut, resetTransform }) => (
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1 }}>
              <Typography id={titleId} variant="body2" noWrap sx={{ flex: 1, minWidth: 0 }}>
                {image.original_name}
                <Typography component="span" variant="caption" sx={{ opacity: 0.7 }}>
                  {`  ${index + 1} / ${images.length}`}
                </Typography>
              </Typography>

              <ViewerButton label="Zoom out" icon={<ViewerIcon sdsIcon="Minus" />} onClick={() => zoomOut()} />
              <ViewerButton label="Zoom in" icon={<ViewerIcon sdsIcon="Plus" />} onClick={() => zoomIn()} />
              <ViewerButton
                label="Fit to screen"
                icon={
                  // SDS has no four-corner arrows icon; inherits the viewer's SDS gray
                  <ZoomOutMapIcon sx={{ fontSize: ICON_PX }} />
                }
                onClick={() => resetTransform()}
              />
              <Tooltip title="Download original">
                <IconButton
                  component="a"
                  href={imageSrc(image, ImageRendition.ORIGINAL)}
                  aria-label="Download original"
                  sx={{ color: 'inherit' }}
                >
                  <ViewerIcon sdsIcon="Download" />
                </IconButton>
              </Tooltip>
              <ViewerButton label="Close" icon={<ViewerIcon sdsIcon="XMark" />} onClick={onClose} />
            </Box>

            <Box sx={{ position: 'relative', flex: 1, minHeight: 0 }}>
              <TransformComponent
                wrapperStyle={{ width: '100%', height: '100%' }}
                contentStyle={{ width: '100%', height: '100%' }}
              >
                <Box
                  component="img"
                  src={imageSrc(image, ImageRendition.PREVIEW)}
                  alt={image.original_name}
                  sx={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
              </TransformComponent>

              {hasPrevious && <StepButton side="left" onClick={() => onIndexChange(index - 1)} />}
              {hasNext && <StepButton side="right" onClick={() => onIndexChange(index + 1)} />}
            </Box>

            {image.notes && (
              <Typography variant="body2" sx={{ px: 2, py: 1.5, whiteSpace: 'pre-wrap' }}>
                {image.notes}
              </Typography>
            )}
          </Box>
        )}
      </TransformWrapper>
    </Dialog>
  );
};

type ViewerIconName = 'Minus' | 'Plus' | 'Download' | 'XMark';

const ViewerIcon: React.FC<{ sdsIcon: ViewerIconName }> = ({ sdsIcon }) => (
  <Icon sdsIcon={sdsIcon} sdsSize="s" color="gray" shade={FOREGROUND_SHADE} />
);

const ViewerButton: React.FC<{ label: string; icon: React.ReactNode; onClick: () => void }> = ({
  label,
  icon,
  onClick,
}) => (
  <Tooltip title={label}>
    <IconButton onClick={onClick} aria-label={label} sx={{ color: 'inherit' }}>
      {icon}
    </IconButton>
  </Tooltip>
);

const StepButton: React.FC<{ side: 'left' | 'right'; onClick: () => void }> = ({ side, onClick }) => (
  <IconButton
    onClick={onClick}
    aria-label={side === 'left' ? 'Previous image' : 'Next image'}
    sx={{
      position: 'absolute',
      top: '50%',
      transform: 'translateY(-50%)',
      [side]: 16,
      bgcolor: 'rgba(0, 0, 0, 0.4)',
      '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.6)' },
    }}
  >
    <Icon
      sdsIcon={side === 'left' ? 'ChevronLeft' : 'ChevronRight'}
      sdsSize="l"
      color="gray"
      shade={FOREGROUND_SHADE}
    />
  </IconButton>
);
