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
  };
}

export const ThumbnailCell: React.FC<ThumbnailCellProps> = memo(({ columnIndex, rowIndex, data }) => {
  const { items } = data;
  const index = rowIndex * 2 + columnIndex;

  if (!items || index >= items.length) {
    return null;
  }

  const item = items[index];

  if (!item || !item.thumbnail_path) {
    return null;
  }

  const thumbnailUrl = item.thumbnail_path;
  console.log(thumbnailUrl, 'thumbnailUrl');

  return (
    <div>
      <div className={styles.thumbnailWrapper}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={thumbnailUrl}
          alt={`Thumbnail for ${item.name || 'item'}`}
          className={styles.thumbnail}
          width={120}
          height={250}
          onError={(e) => {
            console.error(`Failed to load thumbnail: ${thumbnailUrl}`);
            (e.target as HTMLImageElement).alt = 'Thumbnail not available';
          }}
        />
        <Typography variant="caption">{item.name || 'Thumbnail caption'}</Typography>
      </div>
    </div>
  );
});

ThumbnailCell.displayName = 'ThumbnailCell';
