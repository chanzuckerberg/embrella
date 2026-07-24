'use client';

import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Link,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

import type { DatasetSample } from '../../../types';
import { SectionCard } from './SectionCard';

const BIO_ROWS: {
  key: string;
  label: string;
  prefix: string;
  nameKey: keyof DatasetSample;
  idKey: keyof DatasetSample;
  lookup: string;
}[] = [
  { key: 'tissue', label: 'Tissue', prefix: 'UBERON', nameKey: 'tissue_name', idKey: 'tissue_id', lookup: 'https://www.ebi.ac.uk/ols4/ontologies/uberon' },
  { key: 'cell_type', label: 'Cell type', prefix: 'CL', nameKey: 'cell_name', idKey: 'cell_type_id', lookup: 'https://www.ebi.ac.uk/ols4/ontologies/cl' },
  { key: 'cell_strain', label: 'Cell strain', prefix: 'CL', nameKey: 'cell_strain_name', idKey: 'cell_strain_id', lookup: 'https://www.ebi.ac.uk/ols4/ontologies/cl' },
  { key: 'cell_component', label: 'Cell component', prefix: 'GO', nameKey: 'cell_component_name', idKey: 'ontology', lookup: 'https://www.ebi.ac.uk/ols4/ontologies/go' },
  { key: 'development_stage', label: 'Development stage', prefix: 'UBERON', nameKey: 'development_stage_name', idKey: 'development_stage_ontology_id', lookup: 'https://www.ebi.ac.uk/ols4/ontologies/uberon' },
  { key: 'disease', label: 'Disease', prefix: 'CDPO', nameKey: 'disease_name', idKey: 'disease_ontology_id', lookup: 'https://www.ebi.ac.uk/ols4/ontologies/mondo' },
];

function OntologyRow({
  label,
  summary,
  set,
  readOnly,
  children,
  isLast,
}: {
  label: string;
  summary: string;
  set: boolean;
  readOnly: boolean;
  children: React.ReactNode;
  isLast?: boolean;
}) {
  return (
    <Accordion
      disableGutters
      disabled={readOnly}
      sx={{
        '&:before': { display: 'none' },
        boxShadow: 'none',
        bgcolor: 'transparent',
        borderBottom: isLast ? 'none' : '1px solid',
        borderColor: 'divider',
        borderRadius: '0 !important',
      }}
    >
      <AccordionSummary
        expandIcon={<ChevronRightIcon sx={{ color: 'text.secondary', fontSize: 20 }} />}
        sx={{
          px: 2,
          minHeight: 48,
          flexDirection: 'row-reverse',
          '& .MuiAccordionSummary-expandIconWrapper': { mr: 1, ml: 0 },
          '& .MuiAccordionSummary-expandIconWrapper.Mui-expanded': { transform: 'rotate(90deg)' },
          '& .MuiAccordionSummary-content': {
            my: 1.25,
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
            marginLeft: 0,
          },
        }}
      >
        <Typography sx={{ fontWeight: 600 }}>{label}</Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ fontFamily: set ? 'monospace' : 'inherit', fontSize: '0.8125rem' }}
        >
          {summary}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2, pb: 2, pt: 0 }}>{children}</AccordionDetails>
    </Accordion>
  );
}

export function BiologicalClassification({
  sample,
  assayLabel,
  assayOntologyId,
  onChangeSample,
  onChangeAssayLabel,
  onChangeAssayOntologyId,
  readOnly,
  innerRef,
}: {
  sample: DatasetSample;
  assayLabel: string;
  assayOntologyId: string;
  onChangeSample: <K extends keyof DatasetSample>(key: K, value: DatasetSample[K]) => void;
  onChangeAssayLabel: (value: string) => void;
  onChangeAssayOntologyId: (value: string) => void;
  readOnly: boolean;
  innerRef: (el: HTMLDivElement | null) => void;
}) {
  const rowsBeforeAssay = BIO_ROWS.slice(0, 4);
  const rowsAfterAssay = BIO_ROWS.slice(4);

  return (
    <SectionCard
      title="Biological classification"
      badge="Optional"
      badgeTone="primary"
      sectionKey="bioclass"
      collapsible
      defaultExpanded
      innerRef={innerRef}
    >
      <Box
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          overflow: 'hidden',
          bgcolor: 'background.paper',
        }}
      >
        {rowsBeforeAssay.map((row) => {
          const idVal = (sample[row.idKey] as string) || '';
          return (
            <OntologyRow
              key={row.key}
              label={row.label}
              summary={idVal || 'Not set'}
              set={!!idVal}
              readOnly={readOnly}
            >
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
                <TextField
                  label={`${row.label} name`}
                  value={(sample[row.nameKey] as string) ?? ''}
                  onChange={(e) => onChangeSample(row.nameKey, e.target.value)}
                  size="small"
                  fullWidth
                  disabled={readOnly}
                />
                <Chip label={row.prefix} size="small" />
                <TextField
                  label={`${row.label} ID`}
                  value={idVal}
                  onChange={(e) => onChangeSample(row.idKey, e.target.value)}
                  size="small"
                  fullWidth
                  disabled={readOnly}
                />
                <Link
                  href={row.lookup}
                  target="_blank"
                  rel="noopener"
                  variant="body2"
                  sx={{ whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 0.25, fontWeight: 600 }}
                >
                  {row.prefix} lookup <OpenInNewIcon sx={{ fontSize: 14 }} />
                </Link>
              </Stack>
            </OntologyRow>
          );
        })}

        <OntologyRow
          label="Assay"
          summary={assayLabel || 'Not set'}
          set={!!assayLabel}
          readOnly={readOnly}
        >
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
            <TextField
              label="Assay label"
              value={assayLabel}
              onChange={(e) => onChangeAssayLabel(e.target.value)}
              size="small"
              fullWidth
              disabled={readOnly}
            />
            <Chip label="CDPO" size="small" />
            <TextField
              label="Assay ontology ID"
              value={assayOntologyId}
              onChange={(e) => onChangeAssayOntologyId(e.target.value)}
              size="small"
              fullWidth
              disabled={readOnly}
            />
          </Stack>
        </OntologyRow>

        {rowsAfterAssay.map((row, i) => {
          const idVal = (sample[row.idKey] as string) || '';
          const isLast = i === rowsAfterAssay.length - 1;
          return (
            <OntologyRow
              key={row.key}
              label={row.label}
              summary={idVal || 'Not set'}
              set={!!idVal}
              readOnly={readOnly}
              isLast={isLast}
            >
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
                <TextField
                  label={`${row.label} name`}
                  value={(sample[row.nameKey] as string) ?? ''}
                  onChange={(e) => onChangeSample(row.nameKey, e.target.value)}
                  size="small"
                  fullWidth
                  disabled={readOnly}
                />
                <Chip label={row.prefix} size="small" />
                <TextField
                  label={`${row.label} ID`}
                  value={idVal}
                  onChange={(e) => onChangeSample(row.idKey, e.target.value)}
                  size="small"
                  fullWidth
                  disabled={readOnly}
                />
                <Link
                  href={row.lookup}
                  target="_blank"
                  rel="noopener"
                  variant="body2"
                  sx={{ whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 0.25, fontWeight: 600 }}
                >
                  {row.prefix} lookup <OpenInNewIcon sx={{ fontSize: 14 }} />
                </Link>
              </Stack>
            </OntologyRow>
          );
        })}
      </Box>
    </SectionCard>
  );
}
