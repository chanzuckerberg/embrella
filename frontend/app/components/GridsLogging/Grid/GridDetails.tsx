'use client';

import React, { useEffect } from 'react';
import Image from 'next/image';
import { PuckList, UserList } from '@app/common/types/gridLogging';
import { Card, CardContent, CardHeader, Typography, Box, CircularProgress, IconButton } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { useGridDetails } from '@app/common/hooks/useGridLogging/details/useGridDetails';
import styles from '../GridLogging.module.css';
import { MoveGrid } from './MoveGrid';
import { DuplicateGrid } from './DuplicateGrid';
import { TrashGridDialog } from './TrashGridDialog';
import { GridFormFields } from './GridFormFields';
import { useGridForm } from './useGridForm';
import { mapGridDetailsToFormData } from './utils';

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
  onGridMutated?: () => void;
}

export const GridDetails: React.FC<GridDetailsProps> = ({
  selectedPuck,
  selectedSlot,
  selectedGrid,
  selectedGridId,
  selectedUser,
  onGridDetailsRefetchReady,
  onMoveGridSuccess,
  onGridMutated,
}) => {
  const { gridDetails, isSuccess, refetch } = useGridDetails(selectedGridId);

  const form = useGridForm({
    gridId: selectedGridId,
    gridDetails,
    refetch,
    onGridUpdated: onGridMutated,
  });

  useEffect(() => {
    if (onGridDetailsRefetchReady && refetch) {
      onGridDetailsRefetchReady(refetch);
    }
  }, [onGridDetailsRefetchReady, refetch]);

  // Early return if no selection
  if (!selectedPuck || !selectedSlot || !selectedGrid) {
    return null;
  }

  // Show loading state
  if (!isSuccess) {
    return (
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardContent>
          <CircularProgress size={40} />
          <Typography sx={{ mt: 2 }}>Loading grid details...</Typography>
        </CardContent>
      </Card>
    );
  }

  // Show message if no grid details available
  if (!gridDetails || !form.formData) {
    return (
      <Card elevation={2} sx={{ maxWidth: 800, width: '100%' }}>
        <CardContent>
          <Typography>No grid details available</Typography>
        </CardContent>
      </Card>
    );
  }

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
                src={form.clippedValue ? '/clippedGrid.png' : '/grid.png'}
                alt={form.clippedValue ? 'Clipped Grid' : 'Grid'}
                width={150}
                height={150}
                style={{
                  objectFit: 'contain',
                }}
              />
            </Box>

            <Box sx={{ flex: 1, minWidth: 0 }}>
              {/* Edit/Save/Cancel Icons header */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ color: 'primary.main' }}>
                  Grid Details
                </Typography>
                {!form.isEditMode ? (
                  <IconButton
                    onClick={form.handleEditClick}
                    sx={{
                      '&:hover': { backgroundColor: '#e3f2fd' },
                    }}
                  >
                    <Icon sdsIcon="Edit" sdsSize="l" />
                  </IconButton>
                ) : (
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <IconButton
                      onClick={form.handleSaveEdit}
                      disabled={form.isUpdating}
                      sx={{
                        '&:hover': { backgroundColor: '#e8f5e9' },
                        color: 'green',
                      }}
                    >
                      <Icon sdsIcon="CheckCircle" sdsSize="l" color="green" />
                    </IconButton>
                    <IconButton
                      onClick={form.handleCancelEdit}
                      disabled={form.isUpdating}
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
              {!!form.updateError && (
                <Box sx={{ mb: 2, p: 1, bgcolor: '#ffebee', borderRadius: 1 }}>
                  <Typography variant="body2" color="error">
                    {form.updateError}
                  </Typography>
                </Box>
              )}

              <GridFormFields
                formData={form.formData}
                editedData={form.editedData}
                isEditMode={form.isEditMode}
                onFieldChange={form.handleFieldChange}
                clippedValue={form.clippedValue}
                trashedValue={form.trashedValue}
                onClippedChange={form.handleClippedChange}
                onTrashedChange={form.handleTrashedChange}
                currentLabels={form.currentLabels}
                onLabelsChange={form.handleLabelsChange}
                freezingSessions={form.freezingSessions}
                specimens={form.specimens}
                projects={form.projects}
              />

              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button
                  sdsType="primary"
                  sdsStyle="solid"
                  variant="contained"
                  startIcon={<Icon sdsIcon="ChevronUp2" sdsSize="s" />}
                  onClick={() => form.setMoveGridDialogOpen(true)}
                  sx={{ minWidth: 120, fontStyle: 'italic' }}
                >
                  Move Grid
                </Button>
                <Button
                  sdsType="primary"
                  sdsStyle="solid"
                  onClick={() => form.setDuplicateGridDialogOpen(true)}
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
        open={form.moveGridDialogOpen}
        onClose={() => form.setMoveGridDialogOpen(false)}
        currentPuck={selectedPuck}
        currentSlot={selectedSlot}
        currentPosition={selectedGrid}
        gridDetails={gridDetails}
        gridId={selectedGridId}
        selectedUser={selectedUser}
        onSuccess={onMoveGridSuccess}
      />
      <DuplicateGrid
        open={form.duplicateGridDialogOpen}
        onClose={() => form.setDuplicateGridDialogOpen(false)}
        gridDetails={gridDetails}
        gridId={selectedGridId}
        initialLocation={{
          caneId: selectedPuck?.cane ?? null,
          puckId: selectedPuck?.id ?? null,
          slotPosition: selectedSlot ?? null,
        }}
        onSuccess={() => {
          refetch();
          onGridMutated?.();
        }}
      />
      <TrashGridDialog
        open={form.trashDialogOpen}
        onClose={() => form.setTrashDialogOpen(false)}
        onConfirm={form.confirmTrash}
        isProcessing={form.isTrashProcessing}
      />
    </>
  );
};
