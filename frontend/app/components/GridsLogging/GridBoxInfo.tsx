'use client';

import React, { useState } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Card, CardContent, CardHeader, Typography, Box, IconButton, TextField } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import styles from './GridLogging.module.css';
import Image from 'next/image';

interface GridBoxInfoProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  onAddGridBox: () => void;
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

export const GridBoxInfo: React.FC<GridBoxInfoProps> = ({ selectedPuck, selectedSlot, onAddGridBox }) => {
  const [gridBoxData, setGridBoxData] = useState({
    name: '',
    color: 'FFFFFF',
    numbering: 'ucw',
    puck: selectedPuck?.name || '',
    maxGrids: 4,
    positionInPuck: selectedSlot || 1,
  });

  if (!selectedPuck || !selectedSlot) {
    return null;
  }

  const handleInputChange = (field: string, value: any) => {
    setGridBoxData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleDeleteGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/${selectedSlot}/delete/`;
    window.open(adminUrl, '_blank');
    onAddGridBox();
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
    console.log('Save grid box:', gridBoxData);
  };

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
          {/* Left Side: Grid Box SVG */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 200 }}>
            <Image src="/next/GridBox.svg" alt="Grid Box" width={200} height={150} style={{ objectFit: 'contain' }} />
          </Box>

          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
              Grid Box Information
            </Typography>

            {/* Grid box name - single wide field */}
            <TextField
              fullWidth
              label="Grid box name"
              value={gridBoxData.name}
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

            {/* Color and Numbering - two fields side by side */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Color"
                value={GRID_BOX_COLORS.find((c) => c.value === gridBoxData.color)?.label || 'White'}
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
                label="Numbering"
                value={GRID_BOX_NUMBERING.find((n) => n.value === gridBoxData.numbering)?.label || 'U-clockwise'}
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
            </Box>

            {/* Puck and Max Grids - two fields side by side */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                fullWidth
                label="Puck"
                value={gridBoxData.puck}
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
                value={gridBoxData.maxGrids}
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
            </Box>

            {/* Position in puck - single wide field */}
            <TextField
              fullWidth
              label="Position in puck"
              value={gridBoxData.positionInPuck}
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
              startIcon={<Icon sdsIcon="ArrowUp" sdsSize="s" />}
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
