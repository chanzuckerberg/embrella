'use client';

import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { Box, Chip, Link, Stack, TextField } from '@mui/material';

import { SectionCard } from './SectionCard';

export function Organism({
  organismName,
  organismTaxid,
  onChangeOrganismName,
  onChangeOrganismTaxid,
  readOnly,
  innerRef,
}: {
  organismName: string;
  organismTaxid: number | null;
  onChangeOrganismName: (value: string) => void;
  onChangeOrganismTaxid: (value: number | null) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  return (
    <SectionCard title="Organism" sectionKey="organism" innerRef={innerRef}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'flex-start' }}>
        <TextField
          label="Organism name"
          value={organismName}
          onChange={(e) => onChangeOrganismName(e.target.value)}
          size="small"
          sx={{ flex: 1 }}
          disabled={readOnly}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', minHeight: { sm: 40 } }}>
          <Chip label="NCBI" size="small" />
        </Box>
        <TextField
          label="NCBI tax ID"
          required
          value={organismTaxid ?? ''}
          onChange={(e) => onChangeOrganismTaxid(e.target.value === '' ? null : Number(e.target.value))}
          size="small"
          sx={{ flex: 1 }}
          disabled={readOnly}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', minHeight: { sm: 40 } }}>
          <Link
            href="https://www.ncbi.nlm.nih.gov/taxonomy"
            target="_blank"
            rel="noopener"
            variant="body2"
            sx={{
              whiteSpace: 'nowrap',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 0.25,
              fontWeight: 600,
            }}
          >
            NCBI Taxonomy <OpenInNewIcon sx={{ fontSize: 14 }} />
          </Link>
        </Box>
      </Stack>
    </SectionCard>
  );
}
