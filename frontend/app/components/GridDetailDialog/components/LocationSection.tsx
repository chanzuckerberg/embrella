'use client';

import React from 'react';
import Image from 'next/image';
import { Box, Typography } from '@mui/material';
import { PuckSVG } from '@app/components/GridsLogging/Pucks/PuckSvg';
import { GridBoxSVG } from '@app/components/GridsLogging/GridBox/GridBoxSvg';
import { PuckList, PuckSlotsResponse } from '@app/common/types/gridLogging/entities/puckList';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging/details/gridBoxDetails';
import { GridLocation } from '@app/common/types/gridLogging/details/gridDetails';

interface LocationSectionProps {
  location: GridLocation;
  puckForSvg: PuckList | null;
  slotsData: PuckSlotsResponse | undefined;
  gridBoxData: GridBoxDetailResponse | undefined;
  clippedValue: boolean;
}

export const LocationSection: React.FC<LocationSectionProps> = ({
  location,
  puckForSvg,
  slotsData,
  gridBoxData,
  clippedValue,
}) => (
  <Box sx={{ borderTop: 1, borderColor: 'divider', pt: '16px', mt: '8px' }}>
    <Typography sx={{ mb: '12px', fontSize: '0.875rem' }}>Location</Typography>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap', justifyContent: 'left' }}>
      {/* Puck SVG */}
      {puckForSvg && (
        <Box sx={{ textAlign: 'center' }}>
          <PuckSVG
            puck={puckForSvg}
            slots={slotsData?.slots}
            size={120}
            disableSlotClick
            highlightedSlot={location.position_in_puck ?? undefined}
          />
          <Typography variant="caption" display="block" sx={{ mt: '4px' }}>
            Puck: CZII-0{location.puck_name}
          </Typography>
          <Typography variant="caption" display="block">
            Slot: {location.position_in_puck}
          </Typography>
        </Box>
      )}

      {/* Grid Box SVG */}
      {gridBoxData && (
        <Box sx={{ textAlign: 'center' }}>
          <GridBoxSVG
            size={120}
            gridBoxData={gridBoxData}
            selectedGrid={location.position_in_box ?? null}
            disableGridClick
            maxGrids={(gridBoxData.grid_box?.positions?.length as 4 | 6 | 8) ?? 4}
          />
          <Typography variant="caption" display="block" sx={{ mt: '4px' }}>
            Box: {location.grid_box_name}
          </Typography>
          <Typography variant="caption" display="block">
            Position: {location.position_in_box}
          </Typography>
        </Box>
      )}

      {/* Grid image */}
      <Box sx={{ textAlign: 'center' }}>
        <Image
          src={clippedValue ? '/clippedGrid.png' : '/grid.png'}
          alt={clippedValue ? 'Clipped Grid' : 'Unclipped Grid'}
          width={100}
          height={100}
          style={{ objectFit: 'contain' }}
        />
        <Typography variant="caption" display="block" sx={{ mt: '4px' }}>
          {clippedValue ? 'Clipped' : 'Unclipped'}
        </Typography>
      </Box>
    </Box>
  </Box>
);
