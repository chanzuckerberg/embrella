import { useState } from 'react';
import { DJANGO_URL, POST_API } from '@app/common/constants/api';
import {
  useUpdateGrid,
  useFreezingSessionList,
  useSpecimenList,
  useProjectsList,
} from '@app/common/hooks/useGridLogging';
import { GridDetailsResponse } from '@app/common/types/gridLogging/details/gridDetails';
import { FreezingSession } from '@app/common/types/gridLogging/entities/freezingSessionList';
import { Specimen } from '@app/common/types/gridLogging/entities/specimenList';
import { ProjectData } from '@app/common/types/gridLogging/entities/projectList';
import { LabelData } from '@app/components/GridsView/components/LabelEditor/LabelChip';
import { EditedData, GridFormData, mapGridDetailsToFormData } from './utils';

interface UseGridFormOptions {
  gridId: number | null;
  gridDetails: GridDetailsResponse | undefined;
  refetch: () => void;
  onGridUpdated?: () => void;
}

interface UseGridFormReturn {
  // Computed form data
  formData: GridFormData | null;

  // Edit mode
  isEditMode: boolean;
  editedData: EditedData;
  isUpdating: boolean;
  updateError: string | null;
  handleEditClick: () => void;
  handleCancelEdit: () => void;
  handleSaveEdit: () => Promise<void>;
  handleFieldChange: (field: keyof EditedData, value: string | number | null) => void;

  // Checkboxes (immediate save)
  clippedValue: boolean;
  trashedValue: boolean;
  handleClippedChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  handleTrashedChange: (event: React.ChangeEvent<HTMLInputElement>) => void;

  // Labels (immediate save)
  currentLabels: LabelData[];
  handleLabelsChange: (labels: LabelData[]) => void;

  // Move grid dialog
  moveGridDialogOpen: boolean;
  setMoveGridDialogOpen: (open: boolean) => void;

  // Duplicate grid dialog
  duplicateGridDialogOpen: boolean;
  setDuplicateGridDialogOpen: (open: boolean) => void;

  // Trash confirmation dialog
  trashDialogOpen: boolean;
  setTrashDialogOpen: (open: boolean) => void;
  confirmTrash: () => Promise<void>;
  isTrashProcessing: boolean;

  // Dropdown data
  freezingSessions: FreezingSession[] | undefined;
  specimens: Specimen[] | undefined;
  projects: ProjectData[] | undefined;
}

export const useGridForm = ({ gridId, gridDetails, refetch, onGridUpdated }: UseGridFormOptions): UseGridFormReturn => {
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedData, setEditedData] = useState<EditedData>({
    gridName: '',
    copyNumber: 1,
    notes: '',
    freezingSessionId: null,
    specimenId: null,
    projectId: null,
    positionInBox: 1,
    blotTime: 0,
    blotForce: 0,
    blotDistance: 0,
  });
  const [clippedValue, setLocalClipped] = useState(false);
  const [trashedValue, setLocalTrashed] = useState(false);
  const [currentLabels, setCurrentLabels] = useState<LabelData[]>([]);
  const [moveGridDialogOpen, setMoveGridDialogOpen] = useState(false);
  const [duplicateGridDialogOpen, setDuplicateGridDialogOpen] = useState(false);
  const [trashDialogOpen, setTrashDialogOpen] = useState(false);
  const [isTrashProcessing, setIsTrashProcessing] = useState(false);

  const { updateGrid, isUpdating, error: updateError, clearError: clearUpdateError } = useUpdateGrid();
  const { freezingSessions } = useFreezingSessionList();
  const { specimens } = useSpecimenList();
  const { projects } = useProjectsList();

  // Re-sync the editable fields when a fresh API response arrives.
  const [syncedGridDetails, setSyncedGridDetails] = useState(gridDetails);
  if (gridDetails && gridDetails !== syncedGridDetails) {
    setSyncedGridDetails(gridDetails);
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
    setCurrentLabels(formData.labels);
    setLocalClipped(gridDetails.clipped);
    setLocalTrashed(gridDetails.trashed);
  }

  const formData = gridDetails ? mapGridDetailsToFormData(gridDetails) : null;

  const handleEditClick = () => {
    setIsEditMode(true);
    clearUpdateError();
  };

  const handleCancelEdit = () => {
    setIsEditMode(false);
    if (gridDetails) {
      const fd = mapGridDetailsToFormData(gridDetails);
      setEditedData({
        gridName: fd.gridName,
        copyNumber: fd.copyNumber,
        notes: fd.notes,
        freezingSessionId: fd.freezingSessionId,
        specimenId: fd.specimenId,
        projectId: fd.projectId,
        positionInBox: fd.positionInBox,
        blotTime: fd.blotTime,
        blotForce: fd.blotForce,
        blotDistance: fd.blotDistance,
      });
    }
    clearUpdateError();
  };

  const handleSaveEdit = async () => {
    if (!gridId) return;
    const result = await updateGrid({
      grid_id: gridId,
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
    if (result?.success) {
      setIsEditMode(false);
      refetch();
      onGridUpdated?.();
    }
  };

  const handleFieldChange = (field: keyof EditedData, value: string | number | null) => {
    setEditedData((prev) => ({ ...prev, [field]: value }));
  };

  const handleClippedChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!gridId) return;
    const newClippedStatus = event.target.checked;
    setLocalClipped(newClippedStatus);
    try {
      const response = await fetch(`${DJANGO_URL}/cryo_grids/update-grid-clipped/${gridId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ clipped: newClippedStatus }),
      });
      if (!response.ok) setLocalClipped(!newClippedStatus);
    } catch {
      setLocalClipped(!newClippedStatus);
    }
  };

  const handleTrashedChange = async () => {
    if (!gridId || trashedValue) return;
    setTrashDialogOpen(true);
  };

  const confirmTrash = async () => {
    if (!gridId) return;
    setIsTrashProcessing(true);
    setLocalTrashed(true);
    try {
      const response = await fetch(`${DJANGO_URL}/cryo_grids/update-grid-trashed/${gridId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ trashed: true }),
      });
      if (response.ok) {
        setTrashDialogOpen(false);
        refetch();
        onGridUpdated?.();
      } else {
        setLocalTrashed(false);
      }
    } catch {
      setLocalTrashed(false);
    } finally {
      setIsTrashProcessing(false);
    }
  };

  const handleLabelsChange = async (labels: LabelData[]) => {
    setCurrentLabels(labels);
    if (!gridId) return;
    const url = `${DJANGO_URL}${POST_API.UPDATE_GRID_LABELS.replace('grid_id', String(gridId))}`;
    try {
      await fetch(url, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label_ids: labels.map((l) => l.id) }),
      });
    } catch (e) {
      console.error('Failed to update labels:', e);
    }
  };

  return {
    formData,
    isEditMode,
    editedData,
    isUpdating,
    updateError,
    handleEditClick,
    handleCancelEdit,
    handleSaveEdit,
    handleFieldChange,
    clippedValue,
    trashedValue,
    handleClippedChange,
    handleTrashedChange,
    currentLabels,
    handleLabelsChange,
    moveGridDialogOpen,
    setMoveGridDialogOpen,
    duplicateGridDialogOpen,
    setDuplicateGridDialogOpen,
    trashDialogOpen,
    setTrashDialogOpen,
    confirmTrash,
    isTrashProcessing,
    freezingSessions,
    specimens,
    projects,
  };
};
