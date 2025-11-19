'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { useGridLoggingPuckSlots, useClipAllGrids, useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging';
import styles from '../GridLogging.module.css';
import { GridBoxSVG } from './GridBoxSvg';
import { DeleteGridBox } from './DeleteGridBox';
import { disabledTextFieldStyles } from './DisableBoxStyle';
import { UserList, GridBoxDetailResponse, PuckList } from '@app/common/types/gridLogging';
import { AddGrid } from '../Grid/AddGrid';
import { MoveGridBox } from './MoveGridBox';
import { ClipAllGridsDialog } from './ClipAllGridsDialog';

interface GridBoxInfoProps {
  selectedPuck: PuckList | null;
  selectedSlot: number | null;
  onGridSelect: (gridPosition: number, gridId: number) => void;
  selectedUser?: UserList | null;
  onGridDetailsRefetch?: (() => void) | null;
  onMoveGridBoxSuccess?: (newPuckId: number, newSlotPosition: number) => void;
  onGridBoxInfoRefetchReady?: (refetch: () => void) => void;
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

export const GridBoxInfo: React.FC<GridBoxInfoProps> = ({
  selectedPuck,
  selectedSlot,
  onGridSelect,
  selectedUser,
  onGridDetailsRefetch,
  onMoveGridBoxSuccess,
  onGridBoxInfoRefetchReady,
}) => {
  const { slotsData, isSuccess: slotsSuccess } = useGridLoggingPuckSlots(selectedPuck?.id);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [addGridDialogOpen, setAddGridDialogOpen] = useState(false);
  const [clipAllDialogOpen, setClipAllDialogOpen] = useState(false);
  const [isClipping, setIsClipping] = useState(false);
  const [selectedPositionInBox, setSelectedPositionInBox] = useState<number | null>(null);
  const [moveGridBoxDialogOpen, setMoveGridBoxDialogOpen] = useState(false);
  const { gridBoxData, isSuccess: gridBoxSuccess, refetch } = useGridLoggingGridBoxDetail(
    selectedPuck?.id,
    selectedSlot || undefined
  );
  const { clipAllGrids, error: clipError, clearError } = useClipAllGrids();

  useEffect(() => {
    if (onGridBoxInfoRefetchReady) {
      onGridBoxInfoRefetchReady(refetch);
    }
  }, [onGridBoxInfoRefetchReady, refetch]);

 
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
    setDeleteDialogOpen(true);
  };

  const handleAddGrid = (positionInBox?: number) => {
    setAddGridDialogOpen(true);
    setSelectedPositionInBox(positionInBox || null);
  };

  const handleMoveGridBox = () => {
    setMoveGridBoxDialogOpen(true);
  };
  const handleClipAllGrids = () => {
    clearError(); 
    setClipAllDialogOpen(true);
  };

  const handleConfirmClipAll = async () => {
    if (!gridBoxData?.grid_box?.grid_box_id) {
      console.error('No grid box ID available');
      return;
    }

    const result = await clipAllGrids(gridBoxData.grid_box.grid_box_id);
    
    if (result) {
      setClipAllDialogOpen(false);
      // Refetch grid box data to update the UI
      refetch();
      if (onGridDetailsRefetch) {
        onGridDetailsRefetch();
      }
    }
  };

  const unclippedCount = gridBoxData?.grid_box?.positions?.filter(
    (pos) => pos.occupied && !pos.clipped
  ).length || 0;

  const handleGridCreated = (gridPosition: number, gridId: number) => {
    // Refetch grid box data to update the graphic
    refetch();
    // Select the newly created grid (
    onGridSelect(gridPosition, gridId);
  };
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

  return (
    <>
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardHeader
          title={
            <Box className={styles.cardHeader}>
              <Typography variant="h6" component="h2">
                GridBox Name: Puck-CZII-0{selectedPuck.name}/Slot-{formData.positionInPuck}
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
                <Button
                  sdsType="primary"
                  sdsStyle="rounded"
                  startIcon={<Icon sdsIcon="Grid" sdsSize="l" />}
                  onClick={handleClipAllGrids}
                  size="small"
                >
                  Clip All Grids
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
                <TextField
                  fullWidth
                  label="Grid box name"
                  disabled
                  value={formData.name}
                  sx={disabledTextFieldStyles}
                />
                <TextField fullWidth label="Puck" value={formData.puckName} disabled sx={disabledTextFieldStyles} />
              </Box>

              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="Color"
                  value={formData.color_display}
                  disabled
                  sx={disabledTextFieldStyles}
                />
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

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mr: 3 }}>
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
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>
      <DeleteGridBox
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        selectedPuck={selectedPuck}
        selectedSlot={selectedSlot}
        selectedUser={selectedUser}
        gridBoxData={gridBoxData || null}
      />

      <AddGrid
        open={addGridDialogOpen}
        onClose={() => setAddGridDialogOpen(false)}
        selectedUser={selectedUser}
        gridBoxId={gridBoxData?.grid_box?.grid_box_id}
        gridBoxName={gridBoxData?.grid_box?.name}
        positionInBox={selectedPositionInBox || undefined}
        puckId={selectedPuck?.id}
        gridBoxPositionInPuck={selectedSlot}
        onGridCreated={handleGridCreated}
      />

      <MoveGridBox
        open={moveGridBoxDialogOpen}
        onClose={() => setMoveGridBoxDialogOpen(false)}
        currentPuck={selectedPuck}
        currentSlot={selectedSlot}
        gridBoxData={gridBoxData}
        selectedUser={selectedUser}
        onSuccess={(newPuckId: number, newSlotPosition: number) => {
          if (onMoveGridBoxSuccess) {
            onMoveGridBoxSuccess(newPuckId, newSlotPosition);
          }
        }}
      />
      <ClipAllGridsDialog
        open={clipAllDialogOpen}
        onClose={() => {
          setClipAllDialogOpen(false);
          clearError();
        }}
        onConfirm={handleConfirmClipAll}
        gridBoxName={formData.name}
        maxGrids={formData.maxGrids}
        unclippedCount={unclippedCount}
        totalGrids={gridBoxData?.grid_box?.positions?.filter((pos) => pos.occupied).length || 0}
        isProcessing={isClipping}
        error={clipError}
      />
    </>
  );
};
