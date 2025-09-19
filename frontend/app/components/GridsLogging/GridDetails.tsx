'use client';

import React, { useState, useEffect } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField, CircularProgress, Alert, Checkbox, FormControlLabel } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingGridDetails } from '@app/common/hooks/useGridLogging/useGridLoggingGridDetails';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import styles from './GridLogging.module.css';

interface GridDetailsProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  selectedGrid: number | null;
  selectedGridId: number | null;
  onAddGridBox: () => void;
}

export const GridDetails: React.FC<GridDetailsProps> = ({ 
  selectedPuck, 
  selectedSlot, 
  selectedGrid,
  selectedGridId,
  onAddGridBox
}) => {
  // Fetch grid box details to get all grid positions
  const { gridBoxData, isSuccess: gridBoxSuccess } = useGridLoggingGridBoxDetail(
    selectedPuck?.id,
    selectedSlot || undefined
  );

  // Fetch specific grid details if a grid is selected
  const { gridDetails, loading, error } = useGridLoggingGridDetails({
    puckId: selectedPuck?.id || 0,
    positionInPuck: selectedSlot || 0,
    gridId: selectedGridId || 0,
  });

  const [formData, setFormData] = useState({
    gridName: '',
    user: '',
    notes: '',
    clipped: false,
    trashed: false,
    positionInBox: 1,
    copyNumber: 1,
    freezingSession: '',
    specimen: '',
    project: '',
    blotTime: 0,
    blotForce: 0,
    blotDistance: 0,
  });

  console.log(gridDetails, gridBoxData, 'GRID_DETAILS_DATA');

  // Update form data when grid details are loaded
  useEffect(() => {
    if (gridDetails) {
      setFormData({
        gridName: gridDetails.grid_name || '',
        user: gridDetails.user || '',
        notes: gridDetails.notes || '',
        clipped: gridDetails.clipped || false,
        trashed: gridDetails.trashed || false,
        positionInBox: gridDetails.position_in_box || 1,
        copyNumber: gridDetails.copy_number || 1,
        freezingSession: gridDetails.freezing_session?.name || '',
        specimen: gridDetails.specimen?.name || '',
        project: gridDetails.project?.name || '',
        blotTime: gridDetails.parameters?.blot_time || 0,
        blotForce: gridDetails.parameters?.blot_force || 0,
        blotDistance: gridDetails.parameters?.blot_distance || 0,
      });
    }
  }, [gridDetails]);

  if (!selectedPuck || !selectedSlot || !selectedGrid) {
    return null;
  }

  const handleDeleteGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/${selectedGridId}/delete/`;
    window.open(adminUrl, '_blank');
    onAddGridBox();
  };

  const handleAddGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/add/`;
    window.open(adminUrl, '_blank');
  };

  const handleMoveGrid = () => {
    console.log('Move grid');
  };

  const handleSave = () => {
    console.log('Save grid details:', formData);
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

  return (
    <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
      <CardHeader
        title={
          <Box className={styles.cardHeader}>
            <Typography variant="h6" component="h2">
              Grid Details: Puck-{selectedPuck.name}/Slot-{selectedSlot}/Grid-{selectedGrid}
            </Typography>
          </Box>
        }
      />

      <CardContent>
        <Box sx={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
          {/* Left Side: Grid Image */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 200 }}>
            <img
              src="/next/grid.png" 
              alt="Grid"
              style={{
                width: 200,
                height: 200,
                objectFit: 'contain',
                borderRadius: '8px',
              }}
            />
            <Typography variant="caption" sx={{ mt: 1, color: 'primary.main' }}>
              Selected Grid: {selectedGrid}
            </Typography>
          </Box>

          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
              Grid Details
            </Typography>

            {/* Grid name */}
            <TextField
              fullWidth
              label="Grid Name"
              disabled
              value={formData.gridName}
              sx={{ mb: 2 }}
            />

            {/* User */}
            <TextField
              fullWidth
              label="User"
              disabled
              value={formData.user}
              sx={{ mb: 2 }}
            />

            {/* Checkboxes for Clipped and Trashed */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.clipped}
                    color="primary"
                  />
                }
                label="Clipped"
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.trashed}
                    color="primary"
                  />
                }
                label="Trashed"
              />
            </Box>

            {/* Notes and Move Grid */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Notes"
                disabled
                value={formData.notes}
                multiline
                rows={2}
              />
              <Button
                sdsStyle="rounded"
                variant="outlined"
                startIcon={<Icon sdsIcon="ChevronUp2" sdsSize="s" />}
                onClick={handleMoveGrid}
                sx={{ minWidth: 120 }}
              >
                Move Grid
              </Button>
            </Box>

            {/* Freezing Session and Specimen */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Freezing Session"
                disabled
                value={formData.freezingSession}
              />
              <TextField
                fullWidth
                label="Specimen"
                disabled
                value={formData.specimen}
              />
            </Box>

            {/* Project, Position in Box, Copy Number */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Project"
                disabled
                value={formData.project}
              />
              <TextField
                fullWidth
                label="Position in Box"
                disabled
                value={formData.positionInBox}
                type="number"
                inputProps={{ min: 1, max: 4 }}
              />
              <TextField
                fullWidth
                label="Copy Number"
                disabled
                value={formData.copyNumber}
                type="number"
                inputProps={{ min: 1 }}
              />
            </Box>

            {/* Blot Parameters */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Blot Time"
                disabled
                value={formData.blotTime}
                type="number"
                inputProps={{ step: 0.1 }}
              />
              <TextField
                fullWidth
                label="Blot Force"
                disabled
                value={formData.blotForce}
                type="number"
                inputProps={{ step: 0.1 }}
              />
              <TextField
                fullWidth
                label="Blot Distance"
                disabled
                value={formData.blotDistance}
                type="number"
                inputProps={{ step: 0.1 }}
              />
            </Box>

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