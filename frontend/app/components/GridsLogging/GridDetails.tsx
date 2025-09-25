'use client';

import React from 'react';
import Image from 'next/image';
import { PucksList } from '@app/common/types/gridLogging/puckList';
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
  IconButton,
} from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { useGridLoggingGridDetails } from '@app/common/hooks/useGridLogging/useGridLoggingGridDetails';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/useGridLoggingGridBoxDetail';
import styles from './GridLogging.module.css';
import { disabledTextFieldStyles } from './DisableBoxStyle';

interface GridDetailsProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  selectedGrid: number | null;
  selectedGridId: number | null;
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
}) => {
  // Fetch data
  const { isSuccess: gridBoxSuccess } = useGridLoggingGridBoxDetail(selectedPuck?.id, selectedSlot || undefined);

  const { gridDetails, loading, error } = useGridLoggingGridDetails({
    puckId: selectedPuck?.id || 0,
    positionInPuck: selectedSlot || 0,
    gridId: selectedGridId || 0,
  });

  // Early return if no selection
  if (!selectedPuck || !selectedSlot || !selectedGrid) {
    return null;
  }

  const handleMoveGrid = () => {
    console.log('Move grid');
  };

  const handleSave = () => {
    console.log('Save grid details:', formData);
  };
  const handleDeleteGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/${selectedGridId}/delete/`;
    window.location.href = adminUrl;
  };

  const handleDuplicateGrid = () => {
    window.location.href = `${DJANGO_URL}/cryo_grids/grid_detail/${selectedGridId}/`;
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
    <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
      <CardHeader
        title={
          <Box className={styles.cardHeader}>
            <Typography variant="h6" component="h2">
              Grid Name: Puck-{selectedPuck.name}/Slot-{selectedSlot}/Grid-{formData.gridName}
            </Typography>
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
              src="/next/grid.png"
              alt="Grid"
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
              <FormControlLabel control={<Checkbox checked={formData.clipped} color="primary" />} label="Clipped" />
              <FormControlLabel control={<Checkbox checked={formData.trashed} color="primary" />} label="Trashed" />
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
              <TextField
                fullWidth
                label="Copy Number"
                disabled
                value={formData.copyNumber}
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
