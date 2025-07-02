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
  onThumbnailHover?: (positionName: string | null) => void;
  hoveredPosition?: string | null;
}
const Grid = FixedSizeGrid as unknown as React.ComponentType<FixedSizeGridProps<GridData>>;

interface ThumbnailGridProps {
  acceptedResults: TiltSeries[];
  rejectedResults: TiltSeries[];
  data: MetadataVizResponse;
  onThumbnailHover?: (positionName: string | null) => void;
  hoveredPosition?: string | null;
}

const Cell = ({ columnIndex, rowIndex, style, data }: GridChildComponentProps<GridData>) => (
  <div style={style}>
    <ThumbnailCell columnIndex={columnIndex} rowIndex={rowIndex} style={style} data={data} />
  </div>
);

export const ThumbnailGrid: React.FC<ThumbnailGridProps> = memo(
  ({ acceptedResults, rejectedResults, data, onThumbnailHover, hoveredPosition }) => {
    const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });
    const items = data ? acceptedResults : rejectedResults;

    const COLUMN_COUNT = 1;
    const CELL_WIDTH = 425;
    const CELL_HEIGHT = 230;

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

    const gridWidth = Math.min(CELL_WIDTH * COLUMN_COUNT + 32, windowSize.width * 0.28);
    const gridHeight = Math.min(Math.ceil(items.length) * CELL_HEIGHT, windowSize.height * 0.95);

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
          itemData={{ acceptedResults, rejectedResults, items, onThumbnailHover, hoveredPosition }}
        >
          {Cell}
        </Grid>
      </div>
    );
  }
);

ThumbnailGrid.displayName = 'ThumbnailGrid';
