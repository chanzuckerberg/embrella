'use client';

import React, { useState, useEffect } from 'react';
import Image from 'next/image';
import { PuckList } from '@app/common/types/gridLogging/puckList';
import { GridDetailsResponse } from '@app/common/types/gridLogging/gridDetails';
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
} from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingGridDetails } from '@app/common/hooks/useGridLogging/useGridLoggingGridDetails';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import styles from '../GridLogging.module.css';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import { UserList } from '@app/common/types/gridLogging/userList';
import { MoveGrid } from '../Grid/MoveGrid';

interface GridDetailsProps {
  selectedPuck: PuckList | null;
  selectedSlot: number | null;
  selectedGrid: number | null;
  selectedGridId: number | null;
  selectedUser?: UserList | null;
  onGridDetailsRefetchReady?: (refetch: () => void) => void; 
  onMoveGridSuccess?: (newPuckId: number, newSlotPosition: number, newGridBoxId: number, newPositionInBox: number) => void;
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
  specimen: data.specimen?.name || '',
  project: data.project?.name || '',
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
  onMoveGridSuccess
}) => {
  // Fetch data
  const { isSuccess: gridBoxSuccess } = useGridLoggingGridBoxDetail(selectedPuck?.id, selectedSlot || undefined);
  const [moveGridDialogOpen, setMoveGridDialogOpen] = useState(false);

  const { gridDetails, loading, error, refetch } = useGridLoggingGridDetails({
    puckId: selectedPuck?.id || 0,
    positionInPuck: selectedSlot || 0,
    gridId: selectedGridId || 0,
  });
  const [trashedValue, setLocalTrashed] = useState<boolean>(false);
  const [clippedValue, setLocalClipped] = useState<boolean>(false);

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
  // Early return if no selection
  if (!selectedPuck || !selectedSlot || !selectedGrid) {
    return null;
  }

  const handleMoveGrid = () => {
    setMoveGridDialogOpen(true);
  };

  // const handleSave = () => {
  //   console.log('Save grid details:', formData);
  // };
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
        const result = await response.json();
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

  // const handleDeleteGrid = () => {
  //   const prefillParams = new URLSearchParams();

  //   // Add return state parameters
  //   if (selectedUser?.id) {
  //     prefillParams.append('return_user_id', selectedUser.id.toString());
  //   }
  //   if (selectedPuck?.id) {
  //     prefillParams.append('return_puck_id', selectedPuck.id.toString());
  //   }
  //   if (selectedSlot !== null) {
  //     prefillParams.append('return_slot_position', selectedSlot.toString());
  //   }
  //   const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/${selectedGridId}/delete/?${prefillParams.toString()}`;
  //   window.location.href = adminUrl;
  // };

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
            {/* <IconButton
              onClick={handleDeleteGrid}
              sx={{
                '&:hover': {
                  backgroundColor: '#ffebee',
                },
              }}
            >
              <Icon sdsIcon="TrashCan" sdsSize="xl" color="red" />
            </IconButton> */}
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
              src={clippedValue ? "/next/clippedGrid.png" : "/next/grid.png"}
              alt={clippedValue ? "Clipped Grid" : "Grid"}
              width={150}
              height={150}
              style={{
                objectFit: 'contain',
              }}
          />
          </Box>

          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
              Grid Details
            </Typography>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField fullWidth label="Grid Name" disabled value={formData.gridName} sx={disabledTextFieldStyles} />
              <TextField
                fullWidth
                label="Copy Number"
                disabled
                value={formData.copyNumber}
                type="number"
                sx={disabledTextFieldStyles}
              />
              <TextField fullWidth label="User" disabled value={formData.user} sx={disabledTextFieldStyles} />
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Notes"
                disabled
                value={formData.notes}
                multiline
                rows={1}
                sx={disabledTextFieldStyles}
              />
              <FormControlLabel control={<Checkbox checked={clippedValue} onChange={handleClippedGrid} color="primary" />} label="Clipped" /> 
              <FormControlLabel
                control={<Checkbox checked={trashedValue} onChange={handleTrashedGrid} color="primary" />}
                label="Trashed"
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Freezing Session"
                disabled
                value={formData.freezingSession}
                sx={disabledTextFieldStyles}
              />
              <TextField fullWidth label="Specimen" disabled value={formData.specimen} sx={disabledTextFieldStyles} />
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField fullWidth label="Project" disabled value={formData.project} sx={disabledTextFieldStyles} />
              <TextField
                fullWidth
                label="Position in Box"
                disabled
                value={formData.positionInBox}
                type="number"
                sx={disabledTextFieldStyles}
              />
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                fullWidth
                label="Blot Time"
                disabled
                value={formData.blotTime}
                type="number"
                sx={disabledTextFieldStyles}
              />
              <TextField
                fullWidth
                label="Blot Force"
                disabled
                value={formData.blotForce}
                type="number"
                sx={disabledTextFieldStyles}
              />
              <TextField
                fullWidth
                label="Blot Distance"
                disabled
                value={formData.blotDistance}
                type="number"
                sx={disabledTextFieldStyles}
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
              {/* <Button sdsType="primary" sdsStyle="rounded" variant="contained" onClick={handleSave}>
                Save
              </Button> */}
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
