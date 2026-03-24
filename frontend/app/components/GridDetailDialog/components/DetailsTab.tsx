'use client';

import React from 'react';
import Link from 'next/link';
import { Box, IconButton, Typography } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import { LabelData } from '@app/components/GridsView/components/LabelEditor/LabelChip';
import { FreezingSession } from '@app/common/types/gridLogging/entities/freezingSessionList';
import { Specimen } from '@app/common/types/gridLogging/entities/specimenList';
import { ProjectData } from '@app/common/types/gridLogging/entities/projectList';
import { GridFormFields } from '@app/components/GridsLogging/Grid/GridFormFields';
import { EditedData, GridFormData } from '@app/components/GridsLogging/Grid/utils';

interface DetailsTabProps {
  formData: GridFormData;
  gridId: number;

  // Edit mode
  isEditMode: boolean;
  editedData: EditedData;
  onEditClick: () => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onFieldChange: (field: keyof EditedData, value: string | number | null) => void;
  isUpdating: boolean;
  updateError: string | null;

  // Checkboxes (immediate save)
  clippedValue: boolean;
  trashedValue: boolean;
  onClippedChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onTrashedChange: (event: React.ChangeEvent<HTMLInputElement>) => void;

  // Labels (immediate save)
  currentLabels: LabelData[];
  onLabelsChange: (labels: LabelData[]) => void;

  // Dropdown options
  freezingSessions: FreezingSession[] | undefined;
  specimens: Specimen[] | undefined;
  projects: ProjectData[] | undefined;

  // Navigation
  gridLoggingUrl: string | null;

  // Actions
  onMoveGridClick: () => void;
}

export const DetailsTab: React.FC<DetailsTabProps> = ({
  formData,
  gridId,
  isEditMode,
  editedData,
  onEditClick,
  onCancelEdit,
  onSaveEdit,
  onFieldChange,
  isUpdating,
  updateError,
  clippedValue,
  trashedValue,
  onClippedChange,
  onTrashedChange,
  currentLabels,
  onLabelsChange,
  freezingSessions,
  specimens,
  projects,
  gridLoggingUrl,
  onMoveGridClick,
}) => (
  <>
    {/* View in Grid Logging + Edit/Save/Cancel header */}
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
      {gridLoggingUrl !== null && !trashedValue ? (
        <Link
          href={gridLoggingUrl}
          style={{
            fontSize: '0.875rem',
            color: '#1976d2',
            textDecoration: 'underline',
          }}
        >
          View in Grid Logging
        </Link>
      ) : (
        <Box />
      )}
      {!isEditMode ? (
        <IconButton onClick={onEditClick} sx={{ '&:hover': { backgroundColor: '#e3f2fd' } }}>
          <Icon sdsIcon="Edit" sdsSize="l" />
        </IconButton>
      ) : (
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton
            onClick={onSaveEdit}
            disabled={isUpdating}
            sx={{ '&:hover': { backgroundColor: '#e8f5e9' }, color: 'green' }}
          >
            <Icon sdsIcon="CheckCircle" sdsSize="l" color="green" />
          </IconButton>
          <IconButton onClick={onCancelEdit} disabled={isUpdating} sx={{ '&:hover': { backgroundColor: '#ffebee' } }}>
            <Icon sdsIcon="XMark" sdsSize="l" color="red" />
          </IconButton>
        </Box>
      )}
    </Box>

    {!!updateError && (
      <Box sx={{ mb: 2, p: 1, bgcolor: '#ffebee', borderRadius: 1 }}>
        <Typography variant="body2" color="error">
          {updateError}
        </Typography>
      </Box>
    )}

    <GridFormFields
      formData={formData}
      editedData={editedData}
      isEditMode={isEditMode}
      onFieldChange={onFieldChange}
      clippedValue={clippedValue}
      trashedValue={trashedValue}
      onClippedChange={onClippedChange}
      onTrashedChange={onTrashedChange}
      currentLabels={currentLabels}
      onLabelsChange={onLabelsChange}
      freezingSessions={freezingSessions}
      specimens={specimens}
      projects={projects}
    />

    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
      <Button
        sdsType="primary"
        sdsStyle="rounded"
        variant="contained"
        startIcon={<Icon sdsIcon="ChevronUp2" sdsSize="s" />}
        onClick={onMoveGridClick}
        sx={{ minWidth: 120, fontStyle: 'italic' }}
      >
        Move Grid
      </Button>
      <Button
        sdsType="primary"
        sdsStyle="rounded"
        onClick={() => {
          window.location.href = `${DJANGO_URL}/cryo_grids/grid_detail/${gridId}/`;
        }}
        sx={{ minWidth: 120, fontStyle: 'italic' }}
        startIcon={<Icon sdsIcon="Copy" sdsSize="s" />}
      >
        Duplicate Grid
      </Button>
    </Box>
  </>
);
