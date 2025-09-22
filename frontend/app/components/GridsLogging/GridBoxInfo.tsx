'use client';

import React, { useState, useEffect } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging/gridBoxDetails';
import styles from './GridLogging.module.css';
import { GridBoxSVG } from './GridBoxSvg';

interface GridBoxInfoProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  onGridSelect: (gridPosition: number, gridId: number) => void;
}

const mapGridBoxDetailToFormData = (data: GridBoxDetailResponse) => ({
    name: data.grid_box?.name || '',
    color: data.grid_box?.color || 'FFFFFF',
    numbering: data.grid_box?.numbering || 'ucw',
    color_display: data.grid_box?.color_display || 'Neon Pink',
    puckName: data.puck_name || '',
    maxGrids: data.grid_box?.max_grids || data.max_grids || 4,
    positionInPuck: data.position_in_puck || 1,
    numbering_display: data.grid_box?.numbering_display || 'U-counter-clockwise',
  });

export const GridBoxInfo: React.FC<GridBoxInfoProps> = ({ selectedPuck, selectedSlot, onGridSelect }) => {
  // Fetch all puck slots data (same as PuckDetails)
  const { slotsData, isSuccess: slotsSuccess } = useGridLoggingPuckSlots(selectedPuck?.id);

  // Fetch specific grid box details for the selected slot
  const { gridBoxData, isSuccess: gridBoxSuccess } = useGridLoggingGridBoxDetail(
    selectedPuck?.id,
    selectedSlot || undefined
  );

 
const formData = gridBoxData ? mapGridBoxDetailToFormData(gridBoxData) : {
    name: '',
    color: 'FFFFFF',
    numbering: 'ucw',
    color_display: 'Neon Pink',
    puckName: '',
    maxGrids: 4,
    positionInPuck: 1,
    numbering_display: 'U-counter-clockwise',
  };
  console.log(formData, 'FORM_DATA');
  const [selectedGrid, setSelectedGrid] = useState<number | null>(null);

  // Update form data when API data is loaded
 

  if (!selectedPuck || !selectedSlot) {
    return null;
  }

  const handleDeleteGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/${selectedSlot}/delete/`;
    window.open(adminUrl, '_blank');
  };

  const handleAddGrid = () => {
    // Redirect to Django admin for adding grid
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/add/`;
    window.open(adminUrl, '_blank');
  };

  const handleMoveGridBox = () => {
    console.log('Move grid box');
  };

  const handleSave = () => {
    console.log('Save grid box:', formData);
  };

  const handleGridClick = (gridPosition: number) => {
    setSelectedGrid(gridPosition);

    // Check if the grid is occupied (same pattern as handleSlotClick)
    if (gridBoxData?.grid_box?.positions) {
      const gridData = gridBoxData.grid_box.positions.find((p: any) => p.q === gridPosition);
      if (gridData) {
        if (gridData.occupied && gridData.grid_id) {
          onGridSelect(gridPosition, gridData.grid_id);
        } else if (!gridData.occupied) {
          handleAddGrid();
        }
      }
    }
  };

  // Show loading state while fetching data
  if (!slotsSuccess || !gridBoxSuccess) {
    return (
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardContent>
          <Typography>Loading grid box information...</Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
      <CardHeader
        title={
          <Box className={styles.cardHeader}>
            <Typography variant="h6" component="h2">
              GridBox Information: Puck-{selectedPuck.name}/Slot-{selectedSlot}
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <Button
                sdsType="primary"
                sdsStyle="rounded"
                startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
                onClick={handleAddGrid}
                size="small"
              >
                Add Grid
              </Button>
              <IconButton
                onClick={handleDeleteGrid}
                sx={{
                  '&:hover': {
                    backgroundColor: '#ffebee',
                  },
                }}
              >
                <Icon sdsIcon="TrashCan" sdsSize="xl" color="red" />
              </IconButton>
            </Box>
          </Box>
        }
      />

      <CardContent>
        <Box sx={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 200 }}>
            <GridBoxSVG
              size={200}
              onGridClick={handleGridClick}
              gridBoxData={gridBoxData}
              slotsData={slotsData}
              selectedSlot={selectedSlot}
            />
          </Box>

          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
              Grid Box Information
            </Typography>

            {/* Grid box name - single wide field */}
            <TextField
              fullWidth
              label="Grid box name"
              disabled
              value={formData.name}
              sx={{
                mb: 5,
              }}
            />

            {/* Color and Numbering - two fields side by side */}
            <Box sx={{ display: 'flex', gap: 2, mb: 5 }}>
              <TextField fullWidth label="Color" value={formData.color_display} disabled />

              <TextField fullWidth label="Numbering" value={formData?.numbering_display} disabled />
            </Box>

            {/* Puck and Max Grids - two fields side by side */}
            <Box sx={{ display: 'flex', gap: 2, mb: 5 }}>
              <TextField fullWidth label="Puck" value={formData.puckName} disabled />

              <TextField fullWidth label="Max Grids" value={formData.maxGrids} disabled type="number" />
            </Box>

            {/* Position in puck - single wide field */}
            <TextField fullWidth label="Position in puck" value={formData.positionInPuck} disabled />

            {/* Move Grid Box button */}
            <Button
              sdsType="primary"
              sdsStyle="rounded"
              variant="contained"
              startIcon={<Icon sdsIcon="ChevronUp2" sdsSize="s" />}
              onClick={handleMoveGridBox}
              sx={{
                mb: 2,
                mt: 4,
                fontStyle: 'italic',
              }}
            >
              Move Grid Box
            </Button>

            {/* Save Button */}
            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button sdsType="primary" sdsStyle="rounded" variant="contained" onClick={handleSave}>
                Save
              </Button>
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};
