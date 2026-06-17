'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField, MenuItem } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import {
  useGridLoggingPuckSlots,
  useClipAllGrids,
  useGridLoggingGridBoxDetail,
  useUpdateGridBox,
  useGridLoggingChoices,
} from '@app/common/hooks/useGridLogging';
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
  onGridBoxDeleted?: () => void;
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
  onGridBoxDeleted,
}) => {
  const { slotsData, isSuccess: slotsSuccess, refetch: refetchSlots } = useGridLoggingPuckSlots(selectedPuck?.id);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [addGridDialogOpen, setAddGridDialogOpen] = useState(false);
  const [clipAllDialogOpen, setClipAllDialogOpen] = useState(false);
  const [isClipping] = useState(false);
  const [selectedPositionInBox, setSelectedPositionInBox] = useState<number | null>(null);
  const [moveGridBoxDialogOpen, setMoveGridBoxDialogOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedData, setEditedData] = useState({
    name: '',
    color: '',
    numbering: '',
  });

  const {
    gridBoxData,
    isSuccess: gridBoxSuccess,
    refetch,
  } = useGridLoggingGridBoxDetail(selectedPuck?.id, selectedSlot || undefined);
  const { clipAllGrids, error: clipError, clearError } = useClipAllGrids();

  // Add update hook
  const { updateGridBox, isUpdating, error: updateError, clearError: clearUpdateError } = useUpdateGridBox();

  // Add choices hook for dropdowns
  const { choices } = useGridLoggingChoices();

  useEffect(() => {
    if (onGridBoxInfoRefetchReady) {
      onGridBoxInfoRefetchReady(refetch);
    }
  }, [onGridBoxInfoRefetchReady, refetch]);

  // Update edited data when gridBoxData changes
  useEffect(() => {
    if (gridBoxData) {
      const formData = mapGridBoxDetailToFormData(gridBoxData);
      setEditedData({
        name: formData.name,
        color: formData.color,
        numbering: formData.numbering,
      });
    }
  }, [gridBoxData]);

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

  const handleGridBoxDeleted = () => {
    setDeleteDialogOpen(false);
    // Refetch slots data to update puck visualization
    refetchSlots();
    if (onGridBoxDeleted) {
      onGridBoxDeleted();
    }
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

  const unclippedCount = gridBoxData?.grid_box?.positions?.filter((pos) => pos.occupied && !pos.clipped).length || 0;

  const handleGridCreated = (gridPosition: number, gridId: number) => {
    // Refetch grid box data to update the graphic
    refetch();
    // Select the newly created grid (
    onGridSelect(gridPosition, gridId);
  };

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

  // Add edit mode handlers
  const handleEditClick = () => {
    setIsEditMode(true);
    clearUpdateError();
  };

  const handleCancelEdit = () => {
    setIsEditMode(false);
    // Reset edited data to original values
    const formData = mapGridBoxDetailToFormData(gridBoxData);
    setEditedData({
      name: formData.name,
      color: formData.color,
      numbering: formData.numbering,
    });
    clearUpdateError();
  };

  const handleSaveEdit = async () => {
    if (!gridBoxData?.grid_box?.grid_box_id) {
      return;
    }

    const result = await updateGridBox({
      grid_box_id: gridBoxData.grid_box.grid_box_id,
      name: editedData.name,
      color: editedData.color,
      numbering: editedData.numbering,
    });

    if (result && result.success) {
      setIsEditMode(false);
      // Refetch to get updated data
      refetch();
    }
  };

  const handleFieldChange = (field: 'name' | 'color' | 'numbering', value: string) => {
    setEditedData((prev) => ({
      ...prev,
      [field]: value,
    }));
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
                  sdsStyle="solid"
                  startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
                  onClick={() => handleAddGrid()}
                  size="small"
                  disabled={!selectedUser}
                >
                  Add Grid
                </Button>
                <Button
                  sdsType="primary"
                  sdsStyle="solid"
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
                maxGrids={formData.maxGrids as 4 | 6 | 8}
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

            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ color: 'primary.main' }}>
                  GridBox Information
                </Typography>
                {/* Edit/Save Icons */}
                {!isEditMode ? (
                  <IconButton
                    onClick={handleEditClick}
                    sx={{
                      '&:hover': { backgroundColor: '#e3f2fd' },
                    }}
                  >
                    <Icon sdsIcon="Edit" sdsSize="l" />
                  </IconButton>
                ) : (
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <IconButton
                      onClick={handleSaveEdit}
                      disabled={isUpdating}
                      sx={{
                        '&:hover': { backgroundColor: '#e8f5e9' },
                        color: 'green',
                      }}
                    >
                      <Icon sdsIcon="CheckCircle" sdsSize="l" color="green" />
                    </IconButton>
                    <IconButton
                      onClick={handleCancelEdit}
                      disabled={isUpdating}
                      sx={{
                        '&:hover': { backgroundColor: '#ffebee' },
                      }}
                    >
                      <Icon sdsIcon="XMark" sdsSize="l" color="red" />
                    </IconButton>
                  </Box>
                )}
              </Box>

              {/* Show error message if update fails */}
              {!!updateError && (
                <Box sx={{ mb: 2, p: 1, bgcolor: '#ffebee', borderRadius: 1 }}>
                  <Typography variant="body2" color="error">
                    {updateError}
                  </Typography>
                </Box>
              )}

              <Box sx={{ display: 'flex', gap: 2, minWidth: 0 }}>
                <TextField
                  fullWidth
                  label="Grid box name"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.name : formData.name}
                  onChange={(e) => handleFieldChange('name', e.target.value)}
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
                <TextField fullWidth label="Puck" value={formData.puckName} disabled sx={disabledTextFieldStyles} />
              </Box>

              <Box sx={{ display: 'flex', gap: 2, minWidth: 0 }}>
                <TextField
                  fullWidth
                  select={isEditMode}
                  label="Color"
                  value={isEditMode ? editedData.color : formData.color_display}
                  onChange={(e) => handleFieldChange('color', e.target.value)}
                  disabled={!isEditMode}
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                >
                  {isEditMode &&
                    choices?.grid_box_colors?.map((option: { value: string; label: string }) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                </TextField>
                <TextField
                  fullWidth
                  select={isEditMode}
                  label="Numbering"
                  value={isEditMode ? editedData.numbering : formData.numbering_display}
                  onChange={(e) => handleFieldChange('numbering', e.target.value)}
                  disabled={!isEditMode}
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                >
                  {isEditMode &&
                    choices?.grid_box_numbering?.map((option: { value: string; label: string }) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                </TextField>
              </Box>

              <Box sx={{ display: 'flex', gap: 2, minWidth: 0 }}>
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
                  sdsStyle="solid"
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
        gridBoxData={gridBoxData || null}
        onGridBoxDeleted={handleGridBoxDeleted}
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
