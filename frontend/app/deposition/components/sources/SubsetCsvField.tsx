'use client';

import { useRef } from 'react';
import { Button, ButtonIcon, Icon } from '@czi-sds/components';
import { Box, TextField, ToggleButton, ToggleButtonGroup, Tooltip, Typography } from '@mui/material';

import type { SourceRow } from './types';

export function SubsetCsvField({
  row,
  readOnly,
  onChange,
  onUpload,
}: {
  row: SourceRow;
  readOnly: boolean;
  onChange: (patch: Partial<SourceRow>) => void;
  onUpload: (file: File) => void;
}) {
  const mode = row.subset_input_mode ?? 'upload';
  const fileInput = useRef<HTMLInputElement | null>(null);

  const hasFile = row.subset_selection != null || !!row.subset_filename;
  const hasPath = !!row.subset_csv_path;

  const disabledHint = (text: string) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mt: 1 }}>
      <Icon sdsIcon="InfoCircle" sdsSize="xs" color="red" shade={500} />
      <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
        {text}
      </Typography>
    </Box>
  );

  return (
    <Box>
      <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
        Subset selection{' '}
        <Typography component="span" variant="body2" color="text.secondary">
          (this session)
        </Typography>
      </Typography>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={mode}
        onChange={(_, v) => v && onChange({ subset_input_mode: v })}
        disabled={readOnly}
        sx={{
          mb: 1,
          gap: 1,
          '& .MuiToggleButtonGroup-grouped': {
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'divider',
            '&:not(:first-of-type)': { ml: 0, borderLeft: '1px solid', borderColor: 'divider' },
          },
        }}
      >
        <ToggleButton value="upload" sx={{ textTransform: 'none' }}>
          Upload file
        </ToggleButton>
        <ToggleButton value="path" sx={{ textTransform: 'none' }}>
          Cluster path
        </ToggleButton>
      </ToggleButtonGroup>

      {mode === 'upload' ? (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
            <TextField
              fullWidth
              size="small"
              placeholder="No file selected"
              value={row.subset_filename ?? (row.subset_selection ? 'Selection uploaded' : '')}
              InputProps={{
                readOnly: true,
                endAdornment:
                  (row.subset_selection != null || row.subset_filename) && !readOnly ? (
                    <Tooltip title="Remove uploaded file">
                      <ButtonIcon
                        sdsSize="small"
                        sdsType="tertiary"
                        aria-label="Remove uploaded subset file"
                        onClick={() => onChange({ subset_selection: null, subset_filename: undefined })}
                        icon={<Icon sdsIcon="XMark" sdsSize="xs" />}
                      />
                    </Tooltip>
                  ) : null,
              }}
            />
            <input
              ref={fileInput}
              type="file"
              accept=".json,.csv"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onUpload(f);
                e.target.value = '';
              }}
            />
            <Tooltip title={row.id ? 'Upload a subset file' : 'Save the session first, then upload'}>
              <span>
                <Button
                  sdsType="secondary"
                  sdsStyle="outline"
                  disabled={readOnly || !row.id || hasPath}
                  onClick={() => fileInput.current?.click()}
                >
                  Browse
                </Button>
              </span>
            </Tooltip>
          </Box>
          {hasPath && disabledHint('A cluster path is set - remove it to upload a file instead.')}
        </Box>
      ) : (
        <Box>
          <TextField
            fullWidth
            size="small"
            placeholder="/hpc/projects/group.czii/subsets/session.csv"
            value={row.subset_csv_path}
            onChange={(e) => onChange({ subset_csv_path: e.target.value })}
            disabled={readOnly || hasFile}
          />
          {hasFile && disabledHint('A file is uploaded - remove it to enter a cluster path instead.')}
        </Box>
      )}
    </Box>
  );
}
