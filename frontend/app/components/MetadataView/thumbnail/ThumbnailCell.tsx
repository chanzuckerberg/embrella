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
        // Get unit from METRICS_CONFIG
        const metricConfig = METRICS_CONFIG[key as keyof typeof METRICS_CONFIG];
        const unit = metricConfig?.unit || '';
        const label = metricConfig?.label || key;
        const formattedValue = value.toFixed(2);

        return (
          <Typography key={key} sx={{ mb: 0.5 }}>
            {label}: {formattedValue} {unit}
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

  if (!items || index >= items.length) {
    return null;
  }

  const item = items[index];

  if (!item || !item.thumbnail_path || !item.ctf_path) {
    return null;
  }

  // Assuming the primary image is the regular thumbnail_path
  const thumbnailUrl = item.thumbnail_path;
  const ctfUrl = item.ctf_path;

  // Check if this thumbnail should be enlarged (when its position name matches the hovered position)
  // AND the image has loaded successfully

  useEffect(() => {
    const shouldBeEnlarged = hoveredPosition === item.name && thumbnailImageLoaded;
    setIsThumbnailEnlarged(shouldBeEnlarged);
    setIsCTFEnlarged(false);
  }, [hoveredPosition, item.name, thumbnailImageLoaded]);


  const handleMouseEnter = () => {
    if (onThumbnailHover && item.name && thumbnailImageLoaded) {
      onThumbnailHover(item.name);
      setShowThumbnailTooltip(true);
      setIsCTFEnlarged(false);
      setIsThumbnailEnlarged(true);
    }
  };

  const handleMouseLeave = () => {
    if (onThumbnailHover) {
      onThumbnailHover(null);
      setShowThumbnailTooltip(false);
      setIsThumbnailEnlarged(false);
      setIsCTFEnlarged(false);
    }
  };

  const handleCTFMouseEnter = () => {
    if (onThumbnailHover && item.name && ctfImageLoaded) {
      onThumbnailHover(item.name);
      setShowCTFTooltip(true);
      setIsThumbnailEnlarged(false);
      setIsCTFEnlarged(true);
    }
  };

  const handleCTFMouseLeave = () => {
    if (onThumbnailHover) {
      onThumbnailHover(null);
      setShowCTFTooltip(false);
      setIsCTFEnlarged(false);
      setIsThumbnailEnlarged(false);
    }
  };

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