'use client';

import React, { useContext } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import { GridBoxDetailResponse } from '@app/common/types/gridLogging/gridBoxDetails';
import styles from './GridLogging.module.css';
import { GridBoxSVG } from './GridBoxSvg';
import { disabledTextFieldStyles } from './DisableBoxStyle';
import { UserContext } from '@app/common/context/UserProvider';

interface GridBoxInfoProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  onGridSelect: (gridPosition: number, gridId: number) => void;
  selectedUser?: any; // Add selectedUser to props
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

export const GridBoxInfo: React.FC<GridBoxInfoProps> = ({ selectedPuck, selectedSlot, onGridSelect, selectedUser }) => {
  const { slotsData, isSuccess: slotsSuccess } = useGridLoggingPuckSlots(selectedPuck?.id);
  const { gridBoxData, isSuccess: gridBoxSuccess } = useGridLoggingGridBoxDetail(
    selectedPuck?.id,
    selectedSlot || undefined
  );
  const currentUser = useContext(UserContext);

  // Early return if no selection
  if (!selectedPuck || !selectedSlot) {
    return null;
  }

  // Show loading state while fetching data
  if (!slotsSuccess || !gridBoxSuccess || !gridBoxData) {
    return (
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardContent>
          <Typography>Loading grid box information...</Typography>
        </CardContent>
      </Card>
    );
  }

  const formData = mapGridBoxDetailToFormData(gridBoxData);
  // Event handlers
  const handleDeleteGridBox = () => {
    const prefillParams = new URLSearchParams();

    if (selectedUser?.id) {
      prefillParams.append('return_user_id', selectedUser.id.toString());
    }
    if (selectedPuck?.id) {
      prefillParams.append('return_puck_id', selectedPuck.id.toString());
    }

    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogridbox/${selectedSlot}/delete/?${prefillParams.toString()}`;
    window.location.href = adminUrl;
  };

  const handleAddGrid = (positionInBox?: number) => {
    const prefillParams = new URLSearchParams();

    // Prefill grid_box with current grid box ID
    if (gridBoxData?.grid_box?.grid_box_id) {
      prefillParams.append('grid_box', gridBoxData.grid_box.grid_box_id.toString());
    }

    // Prefill position if provided (when called from handleGridClick)
    if (positionInBox !== undefined) {
      prefillParams.append('position_in_box', positionInBox.toString());
    }

    // Get current user from context
    if (currentUser?.id) {
      prefillParams.append('user', currentUser.id);
    }

     // Add return state parameters
     if (selectedUser?.id) {
      prefillParams.append('return_user_id', selectedUser.id.toString());
    }
    if (selectedPuck?.id) {
      prefillParams.append('return_puck_id', selectedPuck.id.toString());
    }
    if (selectedSlot !== null) {
      prefillParams.append('return_slot_position', selectedSlot.toString());
    }

    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/add/?${prefillParams.toString()}`;
    window.location.href = adminUrl;
  };

  // const handleMoveGridBox = () => {
  //   console.log('Move grid box');
  // };

  // const handleSave = () => {
  //   console.log('Save grid box:', formData);
  // };

  const handleGridClick = (gridPosition: number) => {
    if (gridBoxData?.grid_box?.positions) {
      const gridData = gridBoxData.grid_box.positions.find((p) => p.q === gridPosition);
      if (gridData) {
        if (gridData.occupied && gridData.grid_id) {
          onGridSelect(gridPosition, gridData.grid_id);
        } else if (!gridData.occupied) {
          handleAddGrid(gridPosition);
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
              GridBox Name: Puck-{selectedPuck.name}/Slot-{formData.name}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Button
                sdsType="primary"
                sdsStyle="rounded"
                startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
                onClick={() => handleAddGrid()}
                size="small"
              >
                Add Grid
              </Button>
              <IconButton
                onClick={handleDeleteGridBox}
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

      <CardContent sx={{ padding: '0px' }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 200 }}>
            <GridBoxSVG
              size={200}
              onGridClick={handleGridClick}
              gridBoxData={gridBoxData}
              slotsData={slotsData}
              selectedSlot={selectedSlot}
            />
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="body2" component="div" sx={{ marginLeft: '8px' }}>
                Occupied Slots: {gridBoxData?.grid_box?.positions?.filter((pos) => pos.occupied).length || 0} Filled
                with grid
              </Typography>
              <Typography variant="body2" component="div" sx={{ marginLeft: '8px' }}>
                Empty Slots: {gridBoxData?.grid_box?.positions?.filter((pos) => !pos.occupied).length || 0} Empty
              </Typography>
            </Box>
          </Box>

          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
              GridBox Information
            </Typography>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField fullWidth label="Grid box name" disabled value={formData.name} sx={disabledTextFieldStyles} />
              <TextField fullWidth label="Puck" value={formData.puckName} disabled sx={disabledTextFieldStyles} />
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField fullWidth label="Color" value={formData.color_display} disabled sx={disabledTextFieldStyles} />
              <TextField
                fullWidth
                label="Numbering"
                value={formData.numbering_display}
                disabled
                sx={disabledTextFieldStyles}
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Position in puck"
                value={formData.positionInPuck}
                disabled
                sx={disabledTextFieldStyles}
              />
              <TextField
                fullWidth
                label="Max Grids"
                value={formData.maxGrids}
                disabled
                type="number"
                sx={disabledTextFieldStyles}
              />
            </Box>

            {/* <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
               <Button
                sdsType="primary"
                sdsStyle="rounded"
                variant="contained"
                startIcon={<Icon sdsIcon="ChevronUp2" sdsSize="s" />}
                onClick={handleMoveGridBox}
                sx={{ minWidth: 120, fontStyle: 'italic' }}
              >
                Move Grid Box
              </Button> 
              <Button sdsType="primary" sdsStyle="rounded" variant="contained" onClick={handleSave}>
                Save
              </Button>
            </Box> */}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};
