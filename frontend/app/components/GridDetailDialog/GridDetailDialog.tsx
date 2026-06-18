'use client';

import React, { useState } from 'react';
import { Box, CircularProgress, IconButton, Snackbar, Alert, Tab, Tabs, Typography } from '@mui/material';
import LinkIcon from '@mui/icons-material/Link';
import { Dialog, DialogContent, DialogTitle } from '@czi-sds/components';
import { useGridDetails } from '@app/common/hooks/useGridLogging/details/useGridDetails';
import { useGridLoggingPuckSlots } from '@app/common/hooks/useGridLogging/details/useGridLoggingPuckSlots';
import { useGridLoggingGridBoxDetail } from '@app/common/hooks/useGridLogging/details/useGridLoggingGridBoxDetail';
import { PuckList } from '@app/common/types/gridLogging';
import { useGridForm } from '@app/components/GridsLogging/Grid/useGridForm';
import { TrashGridDialog } from '@app/components/GridsLogging/Grid/TrashGridDialog';
import { TabPanel } from './utils';
import { DetailsTab } from './components/DetailsTab';
import { HistoryTab } from './components/HistoryTab';
import { LocationSection } from './components/LocationSection';

// lots of overhead for MoveGrid
const MoveGrid = React.lazy(() =>
  import('@app/components/GridsLogging/Grid/MoveGrid').then((mod) => ({
    default: mod.MoveGrid,
  }))
);

interface GridDetailDialogProps {
  open: boolean;
  onClose: () => void;
  gridId: number | null;
  onGridUpdated?: () => void;
}

export const GridDetailDialog: React.FC<GridDetailDialogProps> = ({ open, onClose, gridId, onGridUpdated }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [copySnackbarOpen, setCopySnackbarOpen] = useState(false);

  const { gridDetails, isSuccess, refetch } = useGridDetails(open ? gridId : null);

  const form = useGridForm({
    gridId,
    gridDetails,
    refetch,
    onGridUpdated,
  });

  // Location data for SVGs
  const location = gridDetails?.location;
  const { slotsData } = useGridLoggingPuckSlots(location?.puck_id ?? undefined);
  const { gridBoxData } = useGridLoggingGridBoxDetail(
    location?.puck_id ?? undefined,
    location?.position_in_puck ?? undefined
  );

  // Reset to the first tab when the dialog opens or the grid changes.
  const [prevOpen, setPrevOpen] = useState(open);
  const [prevGridId, setPrevGridId] = useState(gridId);
  if (open !== prevOpen || gridId !== prevGridId) {
    setPrevOpen(open);
    setPrevGridId(gridId);
    if (open) {
      setActiveTab(0);
    }
  }

  if (!open || !gridId) return null;

  const titleText = gridDetails
    ? `Grid Name: Puck-CZII-0${location?.puck_name ?? '?'}/Slot-${location?.position_in_puck ?? '?'}/Position-${location?.position_in_box ?? '?'}`
    : 'Grid Details';

  const handleMoveGridSuccess = (
    _newPuckId: number,
    _newSlotPosition: number,
    _newGridBoxId: number,
    _newPositionInBox: number
  ) => {
    refetch();
    onGridUpdated?.();
  };

  // Build a minimal PuckList object for PuckSVG
  const puckForSvg: PuckList | null =
    location && slotsData
      ? ({
          id: location.puck_id,
          name: location.puck_name,
          color: location.puck_color ?? '595959',
          color_display: '',
          position_in_cane: 0,
          max_boxes: slotsData.slots?.length ?? 12,
          user_id: 0,
          user_name: '',
          cane: 0,
        } as PuckList)
      : null;

  const handleCopyLink = () => {
    const url = window.location.href;

    if (window.isSecureContext && navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(url).then(() => setCopySnackbarOpen(true));
      return;
    }

    // Fallback for non-HTTPS: use a hidden textarea styled to avoid
    // focus-trap interference from the Dialog overlay.
    const textArea = document.createElement('textarea');
    textArea.value = url;
    Object.assign(textArea.style, {
      position: 'fixed',
      left: '-9999px',
      top: '-9999px',
      opacity: '0',
    });
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    setCopySnackbarOpen(true);
  };

  // Grid logging link
  const gridLoggingUrl =
    location && gridId
      ? `/samples/grid_logging?puck_id=${location.puck_id}&slot_position=${location.position_in_puck}&grid_position=${location.position_in_box}&grid_id=${gridId}&owner=false`
      : null;

  return (
    <>
      <Dialog open={open} onClose={onClose} sdsSize="s" disableScrollLock>
        <DialogTitle
          title={titleText}
          onClose={onClose}
          sx={{ paddingBottom: '0 !important', marginBottom: '0 !important' }}
        />
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ px: 2, display: 'flex', alignItems: 'center', gap: 0.2 }}
        >
          id: {gridId}
          <IconButton onClick={handleCopyLink} size="small" title="Copy link">
            <LinkIcon fontSize="small" />
          </IconButton>
        </Typography>
        <DialogContent>
          {!isSuccess || !gridDetails || !form.formData ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress size={40} />
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Tabs
                value={activeTab}
                onChange={(_, v) => setActiveTab(v)}
                sx={{ borderBottom: 1, borderColor: 'divider' }}
              >
                <Tab label="Details" />
                <Tab label="History" />
              </Tabs>

              <TabPanel value={activeTab} index={0}>
                <DetailsTab
                  formData={form.formData}
                  isEditMode={form.isEditMode}
                  editedData={form.editedData}
                  onEditClick={form.handleEditClick}
                  onCancelEdit={form.handleCancelEdit}
                  onSaveEdit={form.handleSaveEdit}
                  onFieldChange={form.handleFieldChange}
                  isUpdating={form.isUpdating}
                  updateError={form.updateError}
                  clippedValue={form.clippedValue}
                  trashedValue={form.trashedValue}
                  onClippedChange={form.handleClippedChange}
                  onTrashedChange={form.handleTrashedChange}
                  currentLabels={form.currentLabels}
                  onLabelsChange={form.handleLabelsChange}
                  freezingSessions={form.freezingSessions}
                  specimens={form.specimens}
                  projects={form.projects}
                  gridLoggingUrl={gridLoggingUrl}
                  onMoveGridClick={() => form.setMoveGridDialogOpen(true)}
                />
              </TabPanel>

              <TabPanel value={activeTab} index={1}>
                <HistoryTab gridDetails={gridDetails} />
              </TabPanel>

              {/* Location Section (hidden when grid is trashed) */}
              {!form.trashedValue && location && (
                <LocationSection
                  location={location}
                  puckForSvg={puckForSvg}
                  slotsData={slotsData}
                  gridBoxData={gridBoxData}
                  clippedValue={form.clippedValue}
                />
              )}
            </Box>
          )}
        </DialogContent>
      </Dialog>

      <Snackbar
        open={copySnackbarOpen}
        autoHideDuration={3000}
        onClose={() => setCopySnackbarOpen(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setCopySnackbarOpen(false)}
          severity="success"
          sx={{ width: '100%', alignItems: 'center' }}
        >
          Link copied to clipboard
        </Alert>
      </Snackbar>

      {/* MoveGrid Dialog */}
      {gridDetails && location && form.moveGridDialogOpen && (
        <React.Suspense fallback={null}>
          <MoveGrid
            open={form.moveGridDialogOpen}
            onClose={() => form.setMoveGridDialogOpen(false)}
            currentPuck={puckForSvg}
            currentSlot={location.position_in_puck}
            currentPosition={location.position_in_box}
            gridDetails={gridDetails}
            gridId={gridId}
            onSuccess={handleMoveGridSuccess}
          />
        </React.Suspense>
      )}

      <TrashGridDialog
        open={form.trashDialogOpen}
        onClose={() => form.setTrashDialogOpen(false)}
        onConfirm={form.confirmTrash}
        isProcessing={form.isTrashProcessing}
      />
    </>
  );
};
