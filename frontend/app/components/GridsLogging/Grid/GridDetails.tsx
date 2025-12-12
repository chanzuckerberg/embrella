'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import { PuckList, GridDetailsResponse, UserList } from '@app/common/types/gridLogging';
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  TextField,
  CircularProgress,
  Alert,
  Checkbox,
  FormControlLabel,
  IconButton,
  MenuItem,
} from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import {
  useGridLoggingGridDetails,
  useGridLoggingGridBoxDetail,
  useUpdateGrid,
  useFreezingSessionList,
  useSpecimenList,
  useProjectsList,
} from '@app/common/hooks/useGridLogging';
import styles from '../GridLogging.module.css';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { MoveGrid } from '../Grid/MoveGrid';

interface GridDetailsProps {
  selectedPuck: PuckList | null;
  selectedSlot: number | null;
  selectedGrid: number | null;
  selectedGridId: number | null;
  selectedUser?: UserList | null;
  onGridDetailsRefetchReady?: (refetch: () => void) => void;
  onMoveGridSuccess?: (
    newPuckId: number,
    newSlotPosition: number,
    newGridBoxId: number,
    newPositionInBox: number
  ) => void;
}

const mapGridDetailsToFormData = (data: GridDetailsResponse) => ({
  gridName: data.grid_name || '',
  user: data.user || '',
  notes: data.notes || '',
  clipped: data.clipped || false,
  trashed: data.trashed || false,
  positionInBox: data.position_in_box || 1,
  copyNumber: data.copy_number || 1,
  freezingSession: data.freezing_session?.name || '',
  freezingSessionId: data.freezing_session?.id || null,
  specimen: data.specimen?.name || '',
  specimenId: data.specimen?.id || null,
  project: data.project?.name || '',
  projectId: data.project?.id || null,
  blotTime: data.parameters?.blot_time || 0,
  blotForce: data.parameters?.blot_force || 0,
  blotDistance: data.parameters?.blot_distance || 0,
});

export const GridDetails: React.FC<GridDetailsProps> = ({
  selectedPuck,
  selectedSlot,
  selectedGrid,
  selectedGridId,
  selectedUser,
  onGridDetailsRefetchReady,
  onMoveGridSuccess,
}) => {
  // Fetch data
  const { isSuccess: gridBoxSuccess } = useGridLoggingGridBoxDetail(selectedPuck?.id, selectedSlot || undefined);
  const [moveGridDialogOpen, setMoveGridDialogOpen] = useState(false);

  // Fetch list data for dropdowns
  const { freezingSessions } = useFreezingSessionList();
  const { specimens } = useSpecimenList();
  const { projects } = useProjectsList();

  // Add edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedData, setEditedData] = useState({
    gridName: '',
    copyNumber: 1,
    notes: '',
    freezingSessionId: null as number | null,
    specimenId: null as number | null,
    projectId: null as number | null,
    positionInBox: 1,
    blotTime: 0,
    blotForce: 0,
    blotDistance: 0,
  });

  const { gridDetails, loading, error, refetch } = useGridLoggingGridDetails({
    puckId: selectedPuck?.id || 0,
    positionInPuck: selectedSlot || 0,
    gridId: selectedGridId || 0,
  });
  const [trashedValue, setLocalTrashed] = useState<boolean>(false);
  const [clippedValue, setLocalClipped] = useState<boolean>(false);

  // Add update hook
  const { updateGrid, isUpdating, error: updateError, clearError: clearUpdateError } = useUpdateGrid();

  useEffect(() => {
    if (onGridDetailsRefetchReady && refetch) {
      onGridDetailsRefetchReady(refetch);
    }
  }, [onGridDetailsRefetchReady, refetch]);

  useEffect(() => {
    if (gridDetails?.clipped !== undefined) {
      setLocalClipped(gridDetails.clipped);
    }
  }, [gridDetails?.clipped]);

  // Update edited data when gridDetails changes
  useEffect(() => {
    if (gridDetails) {
      const formData = mapGridDetailsToFormData(gridDetails);

      console.log('Grid Details formData:', formData);
      console.log('Freezing Session:', formData.freezingSession);
      console.log('Specimen:', formData.specimen);
      setEditedData({
        gridName: formData.gridName,
        copyNumber: formData.copyNumber,
        notes: formData.notes,
        freezingSessionId: formData.freezingSessionId,
        specimenId: formData.specimenId,
        projectId: formData.projectId,
        positionInBox: formData.positionInBox,
        blotTime: formData.blotTime,
        blotForce: formData.blotForce,
        blotDistance: formData.blotDistance,
      });
    }
  }, [gridDetails]);

  // Early return if no selection
  if (!selectedPuck || !selectedSlot || !selectedGrid) {
    return null;
  }

  const handleMoveGrid = () => {
    setMoveGridDialogOpen(true);
  };

  const handleClippedGrid = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedGridId) return;

    const newClippedStatus = event.target.checked;
    setLocalClipped(newClippedStatus);

    try {
      const response = await fetch(`${DJANGO_URL}/cryo_grids/update-grid-clipped/${selectedGridId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          clipped: newClippedStatus,
        }),
      });

      if (response.ok) {
        await response.json();
      } else {
        setLocalClipped(!newClippedStatus);
      }
    } catch (error) {
      setLocalClipped(!newClippedStatus);
    }
  };

  const handleTrashedGrid = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedGridId) return;

    const newTrashedStatus = event.target.checked;
    setLocalTrashed(newTrashedStatus);

    try {
      const response = await fetch(`${DJANGO_URL}/cryo_grids/update-grid-trashed/${selectedGridId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          trashed: newTrashedStatus,
        }),
      });

      if (response.ok) {
        await response.json();
        // Reload to refresh all data
        window.location.reload();
      } else {
        console.error('Failed to update grid status');
        setLocalTrashed(false);
      }
    } catch (error) {
      console.error('Error updating grid status:', error);
      setLocalTrashed(false);
    }
  };

  const handleDuplicateGrid = () => {
    const prefillParams = new URLSearchParams();

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
    if (selectedGrid !== null) {
      prefillParams.append('return_grid_position', selectedGrid.toString());
    }
    if (selectedGridId !== null) {
      prefillParams.append('return_grid_id', selectedGridId.toString());
    }

    // Use the prefillParams in the URL
    const adminUrl = `${DJANGO_URL}/cryo_grids/grid_detail/${selectedGridId}/?${prefillParams.toString()}`;
    window.location.href = adminUrl;
  };

  // Add edit mode handlers
  const handleEditClick = () => {
    setIsEditMode(true);
    clearUpdateError();
  };

  const handleCancelEdit = () => {
    setIsEditMode(false);
    // Reset edited data to original values
    if (gridDetails) {
      const formData = mapGridDetailsToFormData(gridDetails);
      setEditedData({
        gridName: formData.gridName,
        copyNumber: formData.copyNumber,
        notes: formData.notes,
        freezingSessionId: formData.freezingSessionId,
        specimenId: formData.specimenId,
        projectId: formData.projectId,
        positionInBox: formData.positionInBox,
        blotTime: formData.blotTime,
        blotForce: formData.blotForce,
        blotDistance: formData.blotDistance,
      });
    }
    clearUpdateError();
  };

  const handleSaveEdit = async () => {
    if (!selectedGridId) {
      return;
    }

    const result = await updateGrid({
      grid_id: selectedGridId,
      name: editedData.gridName,
      copy_number: editedData.copyNumber,
      notes: editedData.notes,
      freezing_session: editedData.freezingSessionId === null ? undefined : editedData.freezingSessionId,
      specimen: editedData.specimenId === null ? undefined : editedData.specimenId,
      intended_project: editedData.projectId === null ? undefined : editedData.projectId,
      position_in_box: editedData.positionInBox,
      blot_time: editedData.blotTime,
      blot_force: editedData.blotForce,
      blot_distance: editedData.blotDistance,
    });
    if (result && result.success) {
      setIsEditMode(false);
      // Refetch to get updated data
      refetch();
    }
  };

  const handleFieldChange = (field: keyof typeof editedData, value: string | number | null) => {
    setEditedData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  // Show loading state
  if (!gridBoxSuccess || loading) {
    return (
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardContent>
          <CircularProgress size={40} />
          <Typography sx={{ mt: 2 }}>Loading grid details...</Typography>
        </CardContent>
      </Card>
    );
  }

  // Show error state
  if (error) {
    return (
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardContent>
          <Alert severity="error">Failed to load grid details: {error}</Alert>
        </CardContent>
      </Card>
    );
  }

  // Show message if no grid details available
  if (!gridDetails) {
    return (
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardContent>
          <Typography>No grid details available</Typography>
        </CardContent>
      </Card>
    );
  }

  // Compute form data directly from API response
  const formData = mapGridDetailsToFormData(gridDetails);

  return (
    <>
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardHeader
          title={
            <Box className={styles.cardHeader}>
              <Typography variant="h6" component="h2">
                Grid Name: Puck-CZII-0{selectedPuck.name}/Slot-{selectedSlot}/Position-{formData.positionInBox}
              </Typography>
            </Box>
          }
        />

        <CardContent sx={{ padding: '0px' }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 4 }}>
            <Box
              sx={{
                borderColor: '#debf41',
                borderWidth: '2px',
                borderRadius: '8px',
                marginTop: '20px',
                marginLeft: '7px',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <Image
                src={clippedValue ? '/next/clippedGrid.png' : '/next/grid.png'}
                alt={clippedValue ? 'Clipped Grid' : 'Grid'}
                width={150}
                height={150}
                style={{
                  objectFit: 'contain',
                }}
              />
            </Box>

            <Box sx={{ flex: 1 }}>
              {/* Add Edit/Save/Cancel Icons header */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ color: 'primary.main' }}>
                  Grid Details
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

              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="Grid Name"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.gridName : formData.gridName}
                  onChange={(e) => handleFieldChange('gridName', e.target.value)}
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
                <TextField
                  fullWidth
                  label="Copy Number"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.copyNumber : formData.copyNumber}
                  onChange={(e) => handleFieldChange('copyNumber', parseInt(e.target.value) || 1)}
                  type="number"
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
                <TextField fullWidth label="User" disabled value={formData.user} sx={disabledTextFieldStyles} />
              </Box>

              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="Notes"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.notes : formData.notes}
                  onChange={(e) => handleFieldChange('notes', e.target.value)}
                  multiline
                  rows={1}
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
                <FormControlLabel
                  control={<Checkbox checked={clippedValue} onChange={handleClippedGrid} color="primary" />}
                  label="Clipped"
                />
                <FormControlLabel
                  control={<Checkbox checked={trashedValue} onChange={handleTrashedGrid} color="primary" />}
                  label="Trashed"
                />
              </Box>

              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  select={isEditMode}
                  label="Freezing Session"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.freezingSessionId || '' : formData.freezingSession}
                  onChange={(e) =>
                    handleFieldChange('freezingSessionId', e.target.value ? parseInt(e.target.value) : null)
                  }
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                >
                  <MenuItem value="">
                    <em>None</em>
                  </MenuItem>
                  {freezingSessions?.map((session) => (
                    <MenuItem key={session.id} value={session.id}>
                      {session.display_name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  fullWidth
                  select={isEditMode}
                  label="Specimen"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.specimenId || '' : formData.specimen}
                  onChange={(e) => handleFieldChange('specimenId', e.target.value ? parseInt(e.target.value) : null)}
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                >
                  <MenuItem value="">
                    <em>None</em>
                  </MenuItem>
                  {specimens?.map((specimen) => (
                    <MenuItem key={specimen.id} value={specimen.id}>
                      {specimen.display_name}
                    </MenuItem>
                  ))}
                </TextField>
              </Box>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  select={isEditMode}
                  label="Project"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.projectId || '' : formData.project}
                  onChange={(e) => handleFieldChange('projectId', e.target.value ? parseInt(e.target.value) : null)}
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                >
                  <MenuItem value="">
                    <em>None</em>
                  </MenuItem>
                  {projects?.map((project) => (
                    <MenuItem key={project.id} value={project.id}>
                      {project.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  fullWidth
                  label="Position in Box"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.positionInBox : formData.positionInBox}
                  onChange={(e) => handleFieldChange('positionInBox', parseInt(e.target.value) || 1)}
                  type="number"
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
              </Box>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <TextField
                  fullWidth
                  label="Blot Time"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.blotTime : formData.blotTime}
                  onChange={(e) => handleFieldChange('blotTime', parseFloat(e.target.value) || 0)}
                  type="number"
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
                <TextField
                  fullWidth
                  label="Blot Force"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.blotForce : formData.blotForce}
                  onChange={(e) => handleFieldChange('blotForce', parseFloat(e.target.value) || 0)}
                  type="number"
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
                <TextField
                  fullWidth
                  label="Blot Distance"
                  disabled={!isEditMode}
                  value={isEditMode ? editedData.blotDistance : formData.blotDistance}
                  onChange={(e) => handleFieldChange('blotDistance', parseFloat(e.target.value) || 0)}
                  type="number"
                  sx={!isEditMode ? disabledTextFieldStyles : {}}
                />
              </Box>

              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button
                  sdsType="primary"
                  sdsStyle="rounded"
                  variant="contained"
                  startIcon={<Icon sdsIcon="ChevronUp2" sdsSize="s" />}
                  onClick={handleMoveGrid}
                  sx={{ minWidth: 120, fontStyle: 'italic' }}
                >
                  Move Grid
                </Button>
                <Button
                  sdsType="primary"
                  sdsStyle="rounded"
                  onClick={handleDuplicateGrid}
                  sx={{ minWidth: 120, fontStyle: 'italic' }}
                  startIcon={<Icon sdsIcon="Copy" sdsSize="s" />}
                >
                  Duplicate Grid
                </Button>
              </Box>
            </Box>
          </Box>
        </CardContent>
      </Card>
      <MoveGrid
        open={moveGridDialogOpen}
        onClose={() => setMoveGridDialogOpen(false)}
        currentPuck={selectedPuck}
        currentSlot={selectedSlot}
        currentPosition={selectedGrid}
        gridDetails={gridDetails}
        gridId={selectedGridId}
        selectedUser={selectedUser}
        onSuccess={onMoveGridSuccess}
      />
    </>
  );
};
