'use client';

import { Icon } from '@czi-sds/components';
import { IconButton, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material';

import { bioRequirements } from './bioRequirements';
import { BIO_ROWS } from './bioClassificationRows';
import { SectionCard } from './SectionCard';

const SAMPLE_TYPES: Record<string, string> = {
  organism: 'Whole, intact organism (usually a single-celled microbe)',
  tissue: 'Tissue excised from a multicellular organism',
  organelle: 'Isolated organelle or subcellular fraction (e.g. mitochondria, synaptosomes)',
  virus: 'Virus, virion, or virus-like particle (VLP)',
  cell_line: 'Immortalized / established cell line (e.g. HeLa, HEK293)',
  primary_cell_culture: 'Primary cells freshly isolated from an organism (not immortalized)',
  organoid: 'Self-organized 3D organoid culture',
  in_vitro: 'Purified or reconstituted sample (e.g. proteins, complexes, liposomes)',
  in_silico: 'Computationally simulated / synthetic sample',
  other: 'None of the above',
};

export function Sample({
  sampleType,
  samplePreparation,
  gridPreparation,
  otherSetup,
  onChangeSampleType,
  onChangeSamplePreparation,
  onChangeGridPreparation,
  onChangeOtherSetup,
  readOnly,
  innerRef,
}: {
  sampleType: string;
  samplePreparation: string;
  gridPreparation: string;
  otherSetup: string;
  onChangeSampleType: (value: string) => void;
  onChangeSamplePreparation: (value: string) => void;
  onChangeGridPreparation: (value: string) => void;
  onChangeOtherSetup: (value: string) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  const requirements = bioRequirements(sampleType);
  const requiredLabel = BIO_ROWS.find((row) => row.key === requirements.requiredBioField)?.label;
  const requiredParts = [requirements.organismRequired ? 'organism ID' : null, requiredLabel].filter(Boolean);
  let shortGuidance = 'Organism and classification optional.';
  if (!sampleType) shortGuidance = 'Sets which organism and classification fields are required.';
  else if (requiredParts.length) shortGuidance = `Requires ${requiredParts.join(' and ')}.`;
  const fullGuidance = sampleType
    ? (SAMPLE_TYPES[sampleType] ?? sampleType)
    : 'Choose the type that describes the material imaged.';
  return (
    <SectionCard title="Sample" sectionKey="sample" innerRef={innerRef}>
      <Stack direction="row" spacing={0.5} alignItems="flex-start" sx={{ maxWidth: { sm: 360 } }}>
        <TextField
          select
          label="Sample type"
          value={sampleType}
          onChange={(e) => onChangeSampleType(e.target.value)}
          required
          fullWidth
          size="small"
          disabled={readOnly}
          helperText={shortGuidance}
          SelectProps={{
            renderValue: (value) => value as string,
            MenuProps: { PaperProps: { sx: { maxHeight: 360 } } },
          }}
        >
          {Object.entries(SAMPLE_TYPES).map(([t, description]) => (
            <MenuItem key={t} value={t} sx={{ display: 'block', whiteSpace: 'normal', py: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {t}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {description}
              </Typography>
            </MenuItem>
          ))}
        </TextField>
        <Tooltip title={fullGuidance} arrow placement="top">
          <IconButton size="small" aria-label="Sample type requirements" sx={{ mt: 0.5 }}>
            <Icon sdsIcon="InfoCircle" sdsSize="s" color="purple" />
          </IconButton>
        </Tooltip>
      </Stack>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField
          label="Sample preparation"
          helperText="How the material was prepared before applying to the grid."
          placeholder="e.g. Cells grown in medium, harvested, and resuspended in buffer"
          value={samplePreparation}
          onChange={(e) => onChangeSamplePreparation(e.target.value)}
          multiline
          minRows={4}
          fullWidth
          size="small"
          disabled={readOnly}
          sx={{ '& textarea': { resize: 'vertical' } }}
        />
        <TextField
          label="Grid preparation"
          helperText="Grid type, treatment, blotting, and freezing conditions."
          value={gridPreparation}
          onChange={(e) => onChangeGridPreparation(e.target.value)}
          multiline
          minRows={4}
          fullWidth
          size="small"
          disabled={readOnly}
          placeholder="e.g. glow discharge + blot 3s + plunge in ethane"
          sx={{ '& textarea': { resize: 'vertical' } }}
        />
      </Stack>

      <TextField
        label="Other setup"
        helperText="Optional: extra steps, e.g. cryo-FIB milling."
        value={otherSetup}
        onChange={(e) => onChangeOtherSetup(e.target.value)}
        fullWidth
        size="small"
        disabled={readOnly}
      />
    </SectionCard>
  );
}
