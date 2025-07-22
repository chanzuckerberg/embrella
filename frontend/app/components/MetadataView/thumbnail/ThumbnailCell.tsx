import React, { memo, useState, useEffect } from 'react';
import styles from '../MetadataViz.module.css';
import { Typography, Paper } from '@mui/material';
import { TiltSeries } from '@app/common/types/metadataViz/metadataVizData';
import { METRICS_CONFIG } from '../constants/MetricConfig';

interface ThumbnailCellProps {
  columnIndex: number;
  rowIndex: number;
  style: React.CSSProperties;
  data: {
    acceptedResults?: TiltSeries[];
    rejectedResults?: TiltSeries[];
    items: TiltSeries[];
    onThumbnailHover?: (positionName: string | null) => void;
    hoveredPosition?: string | null;
  };
}

// Custom tooltip component to display metrics information
const ThumbnailTooltip = ({ item }: { item: TiltSeries }) => {
  if (!item || !item.metrics) return null;

  const metrics = item.metrics;

  return (
    <Paper elevation={3} className={styles.thumbnailTooltip}>
      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 3 }}>
        {item.name || 'Unknown'}
      </Typography>

      {Object.entries(metrics).map(([key, value]) => {
        // Skip pixel size
        if (key === 'pixel_size') return null;
        // Get unit from METRICS_CONFIG
        const metricConfig = METRICS_CONFIG[key as keyof typeof METRICS_CONFIG];
        const unit = metricConfig?.unit || '';
        const label = metricConfig?.label || key;
        // Handle null or undefined values
        if (value === null || value === undefined) {
          return (
            <Typography key={key} sx={{ mb: 0.5 }}>
              {label}: N/A {unit}
            </Typography>
          );
        }
        // Apply the same logic as scatter plot tooltip - multiply bad_patch metrics by 100
        const multiplier = key.includes('bad_patch') ? 100 : 1;
        const formattedValue = (value * multiplier).toFixed(2);
        const displayUnit = key.includes('bad_patch') ? '%' : unit;

        return (
          <Typography key={key} sx={{ mb: 0.5 }}>
            {label}: {formattedValue} {displayUnit}
          </Typography>
        );
      })}
    </Paper>
  );
};

export const ThumbnailCell: React.FC<ThumbnailCellProps> = memo(({ columnIndex, rowIndex, data }) => {
  const { items, onThumbnailHover, hoveredPosition } = data;
  const index = rowIndex * 1 + columnIndex;

  // Separate states for each image type
  const [showThumbnailTooltip, setShowThumbnailTooltip] = useState(false);
  const [showCTFTooltip, setShowCTFTooltip] = useState(false);

  // Separate states for tracking if each image is loaded
  const [thumbnailImageLoaded, setThumbnailImageLoaded] = useState(false);
  const [ctfImageLoaded, setCtfImageLoaded] = useState(false);

  // Separate states for tracking if each image is enlarged
  const [isThumbnailEnlarged, setIsThumbnailEnlarged] = useState(false);
  const [isCTFEnlarged, setIsCTFEnlarged] = useState(false);

  // Track if we're currently directly hovering over an image (as opposed to scatter plot hover)
  const [isDirectMouseHover, setIsDirectMouseHover] = useState(false);

  // Get the current item
  const item = items && index < items.length ? items[index] : null;
  const validItem = item && item.thumbnail_path && item.ctf_path;

  // This effect handles hovering from the scatter plot ONLY
  // It won't interfere with direct mouse hovering on images
  useEffect(() => {
    if (!validItem) return;

    // Only handle hover from scatter plot if not directly hovering with mouse
    if (!isDirectMouseHover) {
      if (hoveredPosition === item.name && thumbnailImageLoaded) {
        // When hover comes from scatter plot, only enlarge thumbnail
        setIsThumbnailEnlarged(true);
        setIsCTFEnlarged(false);
        setShowThumbnailTooltip(false);
        setShowCTFTooltip(false);
      } else {
        // Reset all states when hover is removed
        setIsThumbnailEnlarged(false);
        setIsCTFEnlarged(false);
        setShowThumbnailTooltip(false);
        setShowCTFTooltip(false);
      }
    }
  }, [hoveredPosition, item?.name, thumbnailImageLoaded, isDirectMouseHover, validItem]);

  const handleMouseEnter = () => {
    if (validItem && onThumbnailHover && item.name && thumbnailImageLoaded) {
      setIsDirectMouseHover(true);
      onThumbnailHover(item.name);
      // When hovering on thumbnail, only enlarge thumbnail
      setShowThumbnailTooltip(true);
      setShowCTFTooltip(false);
      setIsCTFEnlarged(false);
      setIsThumbnailEnlarged(true);
    }
  };

  const handleMouseLeave = () => {
    if (onThumbnailHover) {
      setIsDirectMouseHover(false);
      onThumbnailHover(null);
      // Reset all states
      setShowThumbnailTooltip(false);
      setIsThumbnailEnlarged(false);
      setShowCTFTooltip(false);
      setIsCTFEnlarged(false);
    }
  };

  const handleCTFMouseEnter = () => {
    if (validItem && onThumbnailHover && item.name && ctfImageLoaded) {
      setIsDirectMouseHover(true);
      onThumbnailHover(item.name);
      // When hovering on CTF, only enlarge CTF
      setShowCTFTooltip(true);
      setIsThumbnailEnlarged(false);
      setShowThumbnailTooltip(false);
      setIsCTFEnlarged(true);
    }
  };

  const handleCTFMouseLeave = () => {
    if (onThumbnailHover) {
      setIsDirectMouseHover(false);
      onThumbnailHover(null);
      // Reset all states
      setShowCTFTooltip(false);
      setShowThumbnailTooltip(false);
      setIsCTFEnlarged(false);
      setIsThumbnailEnlarged(false);
    }
  };

  // Render null for invalid items
  if (!validItem) {
    return null;
  }

  // Assuming the primary image is the regular thumbnail_path
  const thumbnailUrl = item.thumbnail_path;
  const ctfUrl = item.ctf_path;

  return (
    <div className={styles.thumbnailWrapper}>
      <div className={styles.thumbnailPair}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={thumbnailUrl}
          alt={`Thumbnail for ${item.name || 'item'}`}
          className={`${styles.thumbnail} ${isThumbnailEnlarged ? styles.thumbnailEnlarged : ''}`}
          onLoad={() => setThumbnailImageLoaded(true)}
          onError={(e) => {
            console.error(`Failed to load thumbnail: ${thumbnailUrl}`);
            (e.target as HTMLImageElement).alt = 'Thumbnail not available';
            setThumbnailImageLoaded(false);
          }}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        />

        {/* CTF thumbnail */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={ctfUrl}
          alt={`CTF thumbnail for ${item.name || 'item'}`}
          className={`${styles.thumbnail} ${isCTFEnlarged ? styles.thumbnailEnlarged : ''}`}
          onLoad={() => setCtfImageLoaded(true)}
          onError={(e) => {
            console.error(`Failed to load thumbnail: ${ctfUrl}`);
            (e.target as HTMLImageElement).alt = 'Thumbnail not available';
            setCtfImageLoaded(false);
          }}
          onMouseEnter={handleCTFMouseEnter}
          onMouseLeave={handleCTFMouseLeave}
        />
      </div>
      <Typography sx={{ mt: 2 }} variant="caption">
        {item.name || 'Thumbnail caption'}
      </Typography>

      {/* Custom tooltips that appear next to each thumbnail */}
      {showThumbnailTooltip && item && (
        <div className={styles.thumbnailTooltipWrapper} style={{ left: '0px' }}>
          <ThumbnailTooltip item={item} />
        </div>
      )}

      {showCTFTooltip && item && (
        <div className={styles.thumbnailTooltipWrapper} style={{ right: '0px' }}>
          <ThumbnailTooltip item={item} />
        </div>
      )}
    </div>
  );
});
ThumbnailCell.displayName = 'ThumbnailCell';
