import React, { memo } from 'react';
import styles from '../MetadataViz.module.css';
import { Typography } from '@mui/material';
import { TiltSeries } from '@app/common/types/metadataViz/metadataVizData';

interface ThumbnailCellProps {
  columnIndex: number;
  rowIndex: number;
  style: React.CSSProperties;
  data: {
    acceptedResults?: TiltSeries[];
    rejectedResults?: TiltSeries[];
    items: TiltSeries[];
    onThumbnailHover?: (positionName: string | null) => void;
  };
}

export const ThumbnailCell: React.FC<ThumbnailCellProps> = memo(({ columnIndex, rowIndex, data }) => {
  const { items, onThumbnailHover } = data;
  const index = rowIndex * 1 + columnIndex;

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
  
  const handleMouseEnter = () => {
    if (onThumbnailHover && item.name) {
      onThumbnailHover(item.name);
    }
  };

  const handleMouseLeave = () => {
    if (onThumbnailHover) {
      onThumbnailHover(null);
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
            className={styles.thumbnail}
            onError={(e) => {
              console.error(`Failed to load thumbnail: ${thumbnailUrl}`);
              (e.target as HTMLImageElement).alt = 'Thumbnail not available';
            }}
          />
        
        {/* CTF thumbnail */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={ctfUrl}
            alt={`CTF thumbnail for ${item.name || 'item'}`}
            className={styles.thumbnail}
            onError={(e) => {
              console.error(`Failed to load thumbnail: ${ctfUrl}`);
              (e.target as HTMLImageElement).alt = 'Thumbnail not available';
            }}
          />
      </div>
      <Typography variant="caption">{item.name || 'Thumbnail caption'}</Typography>
    </div>
  );
});

ThumbnailCell.displayName = 'ThumbnailCell';