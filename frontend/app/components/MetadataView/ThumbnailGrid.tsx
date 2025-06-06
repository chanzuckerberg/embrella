import React, { useState, useEffect, memo } from 'react';
import { FixedSizeGrid } from 'react-window';
import type { FixedSizeGridProps, GridChildComponentProps } from 'react-window';
import { TiltSeries } from '@app/common/types/metadataViz/metadataVizData';
import styles from './MetadataViz.module.css';
import { Box, Typography } from '@mui/material';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';
import { ThumbnailCell } from './thumbnail/ThumbnailCell';

interface GridData {
  acceptedResults: TiltSeries[];
  rejectedResults: TiltSeries[];
  items: TiltSeries[];
}
const Grid = FixedSizeGrid as unknown as React.ComponentType<FixedSizeGridProps<GridData>>;

interface ThumbnailGridProps {
  acceptedResults: TiltSeries[];
  rejectedResults: TiltSeries[];
  data: MetadataVizResponse;
}

const Cell: React.FC<GridChildComponentProps> = ({ columnIndex, rowIndex, style, data }) => (
  <div style={style}>
    <ThumbnailCell columnIndex={columnIndex} rowIndex={rowIndex} style={style} data={data} />
  </div>
);

export const ThumbnailGrid: React.FC<ThumbnailGridProps> = memo(({ acceptedResults, rejectedResults, data }) => {
  const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });
  const items = data ? acceptedResults : rejectedResults;

  console.log('Data for thumbnail from API', data, acceptedResults, rejectedResults, items);

  const COLUMN_COUNT = 1;
  const CELL_WIDTH = 150;
  const CELL_HEIGHT = 180;

  useEffect(() => {
    const updateWindowSize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    updateWindowSize();
    window.addEventListener('resize', updateWindowSize);
    return () => window.removeEventListener('resize', updateWindowSize);
  }, []);

  const gridWidth = Math.min(CELL_WIDTH * COLUMN_COUNT, windowSize.width * 0.25);
  const gridHeight = Math.min(Math.ceil(items.length / COLUMN_COUNT) * CELL_HEIGHT, windowSize.height * 0.7);

  if (items.length === 0) {
    return (
      <Box className={styles.noThumbnails}>
        <Typography variant="body2">No thumbnails available</Typography>
      </Box>
    );
  }

  return (
    <div className={styles.gridContainer}>
      <Grid
        className={styles.grid}
        columnCount={COLUMN_COUNT}
        columnWidth={CELL_WIDTH}
        height={gridHeight}
        rowCount={Math.ceil(items.length / COLUMN_COUNT)}
        rowHeight={CELL_HEIGHT}
        width={gridWidth}
        itemData={{ acceptedResults, rejectedResults, items }}
      >
        {Cell}
      </Grid>
    </div>
  );
});

ThumbnailGrid.displayName = 'ThumbnailGrid';
