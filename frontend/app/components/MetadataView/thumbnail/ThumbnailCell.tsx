import React, { memo, useState, useMemo } from 'react';
import styles from '../MetadataViz.module.css';
import { Typography, Paper } from '@mui/material';
import { TiltSeries } from '@app/common/types/metadataViz/metadataVizData';
import {METRICS_CONFIG} from '../constants/MetricConfig';

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
      <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 3 }}>
        Position: {item.name || 'Unknown'}
      </Typography>
      
      {Object.entries(metrics).map(([key, value]) => {
      
         // Get unit from METRICS_CONFIG
               const metricConfig = METRICS_CONFIG[key as keyof typeof METRICS_CONFIG];
               const unit = metricConfig?.unit || '';
               const label = metricConfig?.label || key;
               const formattedValue = value.toFixed(2);
        
        return (
          <Typography key={key} variant="body2" sx={{ mb: 0.5 }}>
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
  const [showTooltip, setShowTooltip] = useState(false);
  // Add state to track if the image loaded successfully
  const [imageLoaded, setImageLoaded] = useState(false);

  if (!items || index >= items.length) {
    return null;
  }

  const item = items[index];

  if (!item || !item.thumbnail_path) {
    return null;
  }

  // Assuming the primary image is the regular thumbnail_path
  const thumbnailUrl = item.thumbnail_path;
  
  const ctfUrl = item.ctf_path;
  
  // Check if this thumbnail should be enlarged (when its position name matches the hovered position)
  // AND the image has loaded successfully
  const isEnlarged = hoveredPosition === item.name && imageLoaded;
  
  const handleMouseEnter = () => {
    if (onThumbnailHover && item.name) {
      onThumbnailHover(item.name);
      setShowTooltip(true);
    }
  };

  const handleMouseLeave = () => {
    if (onThumbnailHover) {
      onThumbnailHover(null);
      setShowTooltip(false);
    }
  };
  
  return (
    <div 
      className={styles.thumbnailWrapper}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className={styles.thumbnailPair}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={thumbnailUrl}
          alt={`Thumbnail for ${item.name || 'item'}`}
          className={`${styles.thumbnail} ${isEnlarged ? styles.thumbnailEnlarged : ''}`}
          onLoad={() => setImageLoaded(true)}
          onError={(e) => {
            console.error(`Failed to load thumbnail: ${thumbnailUrl}`);
            (e.target as HTMLImageElement).alt = 'Thumbnail not available';
            setImageLoaded(false);
          }}
        />
      
        {/* CTF thumbnail */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={ctfUrl}
          alt={`CTF thumbnail for ${item.name || 'item'}`}
          className={styles.thumbnail}
          // className={`${styles.thumbnail} ${isEnlarged ? styles.thumbnailEnlarged : ''}`}
          onError={(e) => {
            console.error(`Failed to load thumbnail: ${ctfUrl}`);
            (e.target as HTMLImageElement).alt = 'Thumbnail not available';
          }}
        />
      </div>
      <Typography variant="caption">{item.name || 'Thumbnail caption'}</Typography>
      
      {/* Custom tooltip that appears next to the thumbnail */}
      {showTooltip && item && <ThumbnailTooltip item={item} />}
    </div>
  );
});

ThumbnailCell.displayName = 'ThumbnailCell';