'use client';

import React, { useState, useEffect } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField, CircularProgress, Alert } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingGridDetails } from '@app/common/hooks/useGridLogging/useGridLoggingGridDetails';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import { GridBoxSVG } from './GridBoxSvg';
import styles from './GridLogging.module.css';

interface GridDetailsProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  selectedGrid: number | null;
  selectedGridId: number | null;
}

export const GridDetails: React.FC<GridDetailsProps> = ({ 
  selectedPuck, 
  selectedSlot, 
  selectedGrid,
  selectedGridId,
}) => {
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
  });

  console.log(gridDetails, 'GRID_DETAILS_DATA');

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
      });
    }
  }, [gridDetails]);

  if (!selectedPuck || !selectedSlot || !selectedGrid) {
    return null;
  }

  const handleInputChange = (field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleDeleteGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/${selectedGrid}/delete/`;
    window.open(adminUrl, '_blank');
  };

  const handleAddGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/add/`;
    window.open(adminUrl, '_blank');
  };

  const handleSave = () => {
    console.log('Save grid details:', formData);
  };

  // Show loading state
  if (loading) {
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
        {/* Main Content: Grid Box SVG + Form */}
        <Box sx={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
          {/* Left Side: Interactive Grid Box SVG */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 200 }}>
            <GridBoxSVG
              size={200}
              onGridClick={() => {}} // No grid clicking in details view
              gridBoxData={gridDetails}
              selectedGrid={selectedGrid}
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
              label="Grid name"
              disabled
              value={formData.gridName}
              onChange={(e) => handleInputChange('gridName', e.target.value)}
              sx={{ mb: 2 }}
            />

            {/* User and Position */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="User"
                disabled
                value={formData.user}
                onChange={(e) => handleInputChange('user', e.target.value)}
              />
              <TextField
                fullWidth
                label="Position in Box"
                disabled
                value={formData.positionInBox}
                onChange={(e) => handleInputChange('positionInBox', parseInt(e.target.value) || 1)}
                type="number"
                inputProps={{ min: 1, max: 4 }}
              />
            </Box>

            {/* Copy Number and Status */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Copy Number"
                disabled
                value={formData.copyNumber}
                onChange={(e) => handleInputChange('copyNumber', parseInt(e.target.value) || 1)}
                type="number"
                inputProps={{ min: 1 }}
              />
              <TextField
                fullWidth
                label="Status"
                disabled
                value={formData.trashed ? 'Trashed' : formData.clipped ? 'Clipped' : 'Active'}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: '#f5f5f5',
                    '& fieldset': {
                      borderColor: '#e0e0e0',
                    },
                  },
                }}
              />
            </Box>

            {/* Notes */}
            <TextField
              fullWidth
              label="Notes"
              disabled
              value={formData.notes}
              onChange={(e) => handleInputChange('notes', e.target.value)}
              multiline
              rows={3}
              sx={{ mb: 2 }}
            />

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