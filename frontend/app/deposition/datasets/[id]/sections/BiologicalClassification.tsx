'use client';

import { Icon } from '@czi-sds/components';
import { Accordion, AccordionDetails, AccordionSummary, Box, Typography } from '@mui/material';

import type { DatasetSample } from '../../../types';
import { BIO_ROWS, type BioRow } from './bioClassificationRows';
import type { RequiredBioField } from './bioRequirements';
import { OntologyIdInput } from '../../../components/OntologyIdInput';
import { SectionCard } from './SectionCard';

function OntologyRow({
  label,
  summary,
  set,
  readOnly,
  children,
  isLast,
  required = false,
}: {
  label: string;
  summary: string;
  set: boolean;
  readOnly: boolean;
  children: React.ReactNode;
  isLast?: boolean;
  required?: boolean;
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
        expandIcon={<Icon sdsIcon="ChevronRight" sdsSize="xs" color="gray" />}
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
        <Typography sx={{ fontWeight: 600 }}>
          {label}
          {required && (
            <Box component="span" sx={{ color: 'error.main', ml: 0.5 }}>
              *
            </Box>
          )}
        </Typography>
        <Typography
          variant="body2"
          color={required && !set ? 'error.main' : 'text.secondary'}
          sx={{ fontFamily: set ? 'monospace' : 'inherit', fontSize: '0.8125rem' }}
        >
          {required && !set ? 'Required' : summary}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2, pb: 2, pt: 0 }}>{children}</AccordionDetails>
    </Accordion>
  );
}

export function BiologicalClassification({
  sample,
  requiredBioField,
  assayLabel,
  assayOntologyId,
  onChangeSample,
  onChangeAssayLabel,
  onChangeAssayOntologyId,
  readOnly,
  innerRef,
}: {
  sample: DatasetSample;
  requiredBioField: RequiredBioField;
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

  const renderRow = (row: BioRow, isLast?: boolean) => {
    const idVal = (sample[row.idKey] as string) || '';
    const required = row.key === requiredBioField;
    return (
      <OntologyRow
        key={row.key}
        label={row.label}
        summary={idVal || 'Not set'}
        set={!!idVal}
        readOnly={readOnly}
        isLast={isLast}
        required={required}
      >
        <OntologyIdInput
          label={row.label}
          ontology={row.ontology}
          pattern={row.pattern}
          prefix={row.prefix}
          lookup={row.lookup}
          manualOnly={row.manualOnly}
          idPlaceholder={row.idPlaceholder}
          childrenOf={row.childrenOf}
          required={required}
          name={(sample[row.nameKey] as string) ?? ''}
          id={idVal}
          onChange={({ name, id }) => {
            if (name !== undefined) onChangeSample(row.nameKey, name);
            if (id !== undefined) onChangeSample(row.idKey, id);
          }}
          disabled={readOnly}
        />
      </OntologyRow>
    );
  };

  return (
    <SectionCard
      title="Biological classification"
      badge={requiredBioField ? undefined : 'Optional'}
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
        {rowsBeforeAssay.map((row) => renderRow(row))}

        <OntologyRow label="Assay" summary={assayOntologyId || 'Not set'} set={!!assayOntologyId} readOnly={readOnly}>
          <OntologyIdInput
            label="Assay"
            ontology="efo"
            pattern="^EFO:[0-9]{7}$"
            prefix="EFO"
            lookup="https://www.ebi.ac.uk/ols4/ontologies/efo"
            name={assayLabel}
            id={assayOntologyId}
            onChange={({ name, id }) => {
              if (name !== undefined) onChangeAssayLabel(name);
              if (id !== undefined) onChangeAssayOntologyId(id);
            }}
            disabled={readOnly}
          />
        </OntologyRow>

        {rowsAfterAssay.map((row, i) => renderRow(row, i === rowsAfterAssay.length - 1))}
      </Box>
    </SectionCard>
  );
}
