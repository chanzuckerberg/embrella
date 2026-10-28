'use client';

import { Box, Checkbox, FormControlLabel, Typography } from '@mui/material';

import type { TomogramFlavor, TomogramMetadata } from '../../types';
import { TOMOGRAM_FLAVORS } from '../../types';
import { isIssue, perFlavorTomogramFields } from './fields';
import { FieldGrid, NothingToFix } from './FieldGrid';
import type { FieldValue } from './MetadataRow';

const FLAVOR_LABEL: Record<TomogramFlavor, string> = {
  denoised: 'Denoised',
  filtered: 'Filtered',
};

const FLAVOR_FILE_SUFFIX: Record<TomogramFlavor, string> = {
  denoised: '_Vol.mrc',
  filtered: '_dctf_Vol.mrc',
};

export function TomogramPanel({
  tomograms,
  readOnly,
  loading,
  columns,
  runName,
  showOnlyIssues,
  onFlavor,
}: {
  tomograms: Record<TomogramFlavor, TomogramMetadata>;
  readOnly: boolean;
  loading: boolean;
  columns: 1 | 2;
  runName: string;
  showOnlyIssues: boolean;
  onFlavor: (flavor: TomogramFlavor, key: string, value: FieldValue) => void;
}) {
  const flavorFields = (flavor: TomogramFlavor) =>
    perFlavorTomogramFields(flavor).filter((f) => !showOnlyIssues || isIssue(f, tomograms[flavor] as never));

  if (showOnlyIssues && TOMOGRAM_FLAVORS.every((f) => flavorFields(f).length === 0)) {
    return <NothingToFix />;
  }

  return (
    <Box sx={{ mt: 0.5 }}>
      {TOMOGRAM_FLAVORS.map((flavor) => {
        const fields = flavorFields(flavor);
        if (fields.length === 0) return null;
        return (
          <Box key={flavor} sx={{ mb: 2.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1 }}>
              <Typography variant="overline" sx={{ fontWeight: 700, letterSpacing: 1, color: 'text.secondary' }}>
                {FLAVOR_LABEL[flavor].toUpperCase()}
                <Box
                  component="span"
                  sx={{ ml: 1, textTransform: 'none', letterSpacing: 0, color: 'text.disabled', fontWeight: 400 }}
                >
                  · {runName ? `${runName}${FLAVOR_FILE_SUFFIX[flavor]}` : `*${FLAVOR_FILE_SUFFIX[flavor]}`}
                </Box>
              </Typography>
              <FormControlLabel
                control={
                  <Checkbox
                    size="small"
                    checked={tomograms[flavor].is_visualization_default === true}
                    disabled={readOnly}
                    onChange={(e) => onFlavor(flavor, 'is_visualization_default', e.target.checked)}
                    sx={{ p: 0.5 }}
                  />
                }
                label={<Typography variant="caption">is_visualization_default</Typography>}
                sx={{ m: 0 }}
              />
            </Box>
            <FieldGrid
              fields={fields}
              meta={tomograms[flavor] as Record<string, FieldValue>}
              columns={columns}
              readOnly={readOnly}
              loading={loading}
              onChange={(key, v) => onFlavor(flavor, key, v)}
            />
          </Box>
        );
      })}
    </Box>
  );
}
