'use client';

import { FormControl, FormControlLabel, MenuItem, Radio, RadioGroup, Select } from '@mui/material';

import type { Dataset } from '../../../types';
import { datasetLabel, type DatasetChoice } from './types';

export function DatasetChoiceField({
  choice,
  onChoiceChange,
  existingDatasetId,
  onExistingDatasetIdChange,
  datasets,
}: {
  choice: DatasetChoice;
  onChoiceChange: (choice: DatasetChoice) => void;
  existingDatasetId: string;
  onExistingDatasetIdChange: (id: string) => void;
  datasets: Dataset[];
}) {
  return (
    <>
      <RadioGroup value={choice} onChange={(_, v) => onChoiceChange(v as DatasetChoice)}>
        <FormControlLabel
          value="new"
          control={<Radio size="small" />}
          label="Reserve new dataset under this deposition"
          sx={{ mt: -5 }}
        />
        <FormControlLabel
          value="existing"
          control={<Radio size="small" />}
          label={
            <FormControl size="small" sx={{ minWidth: 260, mb: 6 }} disabled={choice !== 'existing'}>
              <Select
                displayEmpty
                value={existingDatasetId}
                onChange={(e) => onExistingDatasetIdChange(String(e.target.value))}
              >
                <MenuItem value="" disabled>
                  Use existing dataset…
                </MenuItem>
                {datasets.map((ds) => (
                  <MenuItem key={ds.id} value={String(ds.id)}>
                    {datasetLabel(ds.dataset_id)} - {ds.title || '(untitled)'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          }
        />
      </RadioGroup>
    </>
  );
}
