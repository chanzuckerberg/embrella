import React, { useState, useEffect, memo, useRef } from 'react';
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
const Grid = FixedSizeGrid as unknown as React.ForwardRefExoticComponent<
  FixedSizeGridProps<GridData> & React.RefAttributes<FixedSizeGrid>
>;

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
    const gridRef = useRef<FixedSizeGrid>(null);

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

    // Effect to scroll to the hovered position when it changes
    useEffect(() => {
      if (hoveredPosition && gridRef.current) {
        // Find the index of the hovered position in the items array
        const index = items.findIndex((item) => item.name === hoveredPosition);

        if (index !== -1) {
          // Calculate the row index (since we have a single column)
          const rowIndex = Math.floor(index / COLUMN_COUNT);

          // Use scrollToItem method of the Grid component
          try {
            gridRef.current.scrollToItem({
              align: 'smart',
              columnIndex: 0,
              rowIndex,
            });
          } catch (err) {
            console.error('Error scrolling to item:', err);
          }
        }
      }
    }, [hoveredPosition, items, COLUMN_COUNT]);

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
          ref={gridRef}
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
