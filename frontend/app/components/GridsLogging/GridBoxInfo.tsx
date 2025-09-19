'use client';

import React, { useState, useEffect } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/useGridLoggingPuckSlots';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import styles from './GridLogging.module.css';
import { GridBoxSVG } from './GridBoxSvg';

interface GridBoxInfoProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  onGridSelect: (gridPosition: number, gridId: number) => void;
}

// Color options from choices.py
const GRID_BOX_COLORS = [
  { value: 'CF1E01', label: 'Red' },
  { value: 'fdb000', label: 'Orange' },
  { value: 'fff500', label: 'Yellow' },
  { value: '9eef66', label: 'Green' },
  { value: '00cdf5', label: 'Sky' },
  { value: '366de1', label: 'Blue' },
  { value: 'd728c9', label: 'Purple' },
  { value: 'fd5c9f', label: 'Neon Pink' },
  { value: 'FFFFFF', label: 'White' },
  { value: 'd4d2c5', label: 'Grey' },
  { value: 'ffc08a', label: 'Brown' },
  { value: '000000', label: 'Black' },
];

// Numbering options from choices.py
const GRID_BOX_NUMBERING = [
  { value: 'ucw', label: 'U-clockwise' },
  { value: 'uccw', label: 'U-counter-clockwise' },
  { value: 'z', label: 'Z-top-left' },
];

export const GridBoxInfo: React.FC<GridBoxInfoProps> = ({ 
  selectedPuck, 
  selectedSlot, 
  onGridSelect 
}) => {
  // Fetch all puck slots data (same as PuckDetails)
  const { slotsData, isSuccess: slotsSuccess } = useGridLoggingPuckSlots(selectedPuck?.id);
  
  // Fetch specific grid box details for the selected slot
  const { gridBoxData, isSuccess: gridBoxSuccess } = useGridLoggingGridBoxDetail(
    selectedPuck?.id,
    selectedSlot || undefined
  );

  const [formData, setFormData] = useState({
    name: '',
    color: 'FFFFFF',
    numbering: 'ucw',
    puck: '',
    maxGrids: 4,
    positionInPuck: 1,
  });

  const [selectedGrid, setSelectedGrid] = useState<number | null>(null);

  // Update form data when API data is loaded
  useEffect(() => {
    if (gridBoxSuccess && gridBoxData) {
      setFormData({
        name: gridBoxData.grid_box?.name || '',
        color: gridBoxData.grid_box?.color || 'FFFFFF',
        numbering: gridBoxData.grid_box?.numbering || 'ucw',
        puck: gridBoxData.puckname || '',
        maxGrids: gridBoxData.grid_box?.max_grids || gridBoxData.max_grids || 4,
        positionInPuck: gridBoxData.position_in_puck || 1,
      });
    }
  }, [gridBoxSuccess, gridBoxData]);

  if (!selectedPuck || !selectedSlot) {
    return null;
  }

  const handleInputChange = (field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

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
    console.log('Grid clicked:', gridPosition);
    // setSelectedGrid(gridPosition);
  
    // Check if the grid is occupied (same pattern as handleSlotClick)
    if (gridBoxData?.grid_box?.positions) {
      const gridData = gridBoxData.grid_box.positions.find((p: any) => p.q === gridPosition);
      console.log(gridData?.occupied, gridData?.grid_id, 'GRID_DATA');
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
        {/* Main Content: Grid Box SVG + Form */}
        <Box sx={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
          {/* Left Side: Interactive Grid Box SVG */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 200 }}>
            <GridBoxSVG
              size={200}
              onGridClick={handleGridClick}
              gridBoxData={gridBoxData}
              slotsData={slotsData}
              selectedSlot={selectedSlot}
            />
            {selectedGrid && (
              <Typography variant="caption" sx={{ mt: 1, color: 'primary.main' }}>
                Selected Grid: {selectedGrid}
              </Typography>
            )}
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
              onChange={(e) => handleInputChange('name', e.target.value)}
              sx={{
                mb: 2,
              }}
            />

            {/* Color and Numbering - two fields side by side */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Color"
                value={GRID_BOX_COLORS.find((c) => c.value === formData.color)?.label || 'White'}
                disabled
                onChange={(e) => {
                  const selectedColor = GRID_BOX_COLORS.find((c) => c.label === e.target.value);
                  if (selectedColor) {
                    handleInputChange('color', selectedColor.value);
                  }
                }}
                select
                SelectProps={{
                  native: true,
                }}
              >
                {GRID_BOX_COLORS.map((color) => (
                  <option key={color.value} value={color.label}>
                    {color.label}
                  </option>
                ))}
              </TextField>

              <TextField
                fullWidth
                label="Numbering"
                value={GRID_BOX_NUMBERING.find((n) => n.value === formData.numbering)?.label || 'U-clockwise'}
                disabled
                onChange={(e) => {
                  const selectedNumbering = GRID_BOX_NUMBERING.find((n) => n.label === e.target.value);
                  if (selectedNumbering) {
                    handleInputChange('numbering', selectedNumbering.value);
                  }
                }}
                select
                SelectProps={{
                  native: true,
                }}
              >
                {GRID_BOX_NUMBERING.map((numbering) => (
                  <option key={numbering.value} value={numbering.label}>
                    {numbering.label}
                  </option>
                ))}
              </TextField>
            </Box>

            {/* Puck and Max Grids - two fields side by side */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Puck"
                value={formData.puck}
                disabled
                sx={{
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: '#f5f5f5',
                    '& fieldset': {
                      borderColor: '#e0e0e0',
                    },
                  },
                }}
              />

              <TextField
                fullWidth
                label="Max Grids"
                value={formData.maxGrids}
                disabled
                onChange={(e) => handleInputChange('maxGrids', parseInt(e.target.value) || 4)}
                type="number"
                inputProps={{ min: 1, max: 10 }}
              />
            </Box>

            {/* Position in puck - single wide field */}
            <TextField
              fullWidth
              label="Position in puck"
              value={formData.positionInPuck}
              disabled
              sx={{
                mb: 2,
                '& .MuiOutlinedInput-root': {
                  backgroundColor: '#f5f5f5',
                  '& fieldset': {
                    borderColor: '#e0e0e0',
                  },
                },
              }}
            />

            {/* Move Grid Box button */}
            <Button
              sdsType="primary"
              sdsStyle="rounded"
              variant="contained"
              startIcon={<Icon sdsIcon="ChevronUp2" sdsSize="s" />}
              onClick={handleMoveGridBox}
              sx={{
                mb: 2,
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