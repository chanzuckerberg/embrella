'use client';

import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { Box, InputAdornment, Link, TextField } from '@mui/material';

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
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1.4fr 1fr auto' },
          gap: 2,
          alignItems: 'start',
        }}
      >
        <TextField
          label="Organism name"
          value={organismName}
          onChange={(e) => onChangeOrganismName(e.target.value)}
          fullWidth
          size="small"
          disabled={readOnly}
        />
        <TextField
          label="NCBI tax ID"
          required
          value={organismTaxid ?? ''}
          onChange={(e) => onChangeOrganismTaxid(e.target.value === '' ? null : Number(e.target.value))}
          size="small"
          fullWidth
          disabled={readOnly}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start" sx={{ mr: 0.5 }}>
                <Box
                  sx={{
                    px: 1,
                    py: 0.25,
                    borderRadius: 1,
                    bgcolor: 'grey.100',
                    color: 'text.secondary',
                    fontSize: 12,
                    fontWeight: 700,
                    lineHeight: 1.4,
                  }}
                >
                  NCBI
                </Box>
              </InputAdornment>
            ),
          }}
        />
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
            mt: { sm: 3.25 },
            fontWeight: 600,
          }}
        >
          NCBI Taxonomy <OpenInNewIcon sx={{ fontSize: 14 }} />
        </Link>
      </Box>
    </SectionCard>
  );
}
