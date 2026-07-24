'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@czi-sds/components';
import AddIcon from '@mui/icons-material/Add';
import { Box, Stack } from '@mui/material';

import { updateDataset } from '../../services/depositionApi';
import { depositionKeys } from '../../queryKeys';
import type { AuthorEntry, CrossRef, Dataset, DatasetFunding, DatasetSample } from '../../types';
import { type AutoSaveState, useDraftAutoSave } from '../../hooks/useDraftAutoSave';
import { useDeposition } from '../../hooks/useDeposition';
import { CrossReferencesEditor } from '../../depositions/CrossReferencesEditor';
import { Authors } from './sections/Authors';
import { BasicDetails } from './sections/BasicDetails';
import { BiologicalClassification } from './sections/BiologicalClassification';
import { Funding } from './sections/Funding';
import { Organism } from './sections/Organism';
import { Sample } from './sections/Sample';
import { SectionCard } from './sections/SectionCard';
import { type NavItem, SideNav } from './sections/SideNav';

const splitCsv = (s?: string): string[] =>
  (s ?? '')
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean);

interface FormState {
  title: string;
  description: string;
  sample_preparation: string;
  grid_preparation: string;
  other_setup: string;
  assay_label: string;
  assay_ontology_id: string;
  is_authors_same_as_deposition: boolean;
  authors: AuthorEntry[];
  funding: DatasetFunding[];
  crossRefs: CrossRef[];
  sample: DatasetSample;
}

function toForm(d: Dataset): FormState {
  const s = d.sample ?? {};
  return {
    title: d.title ?? '',
    description: d.description ?? '',
    sample_preparation: d.sample_preparation ?? '',
    grid_preparation: d.grid_preparation ?? '',
    other_setup: d.other_setup ?? '',
    assay_label: d.assay_label ?? '',
    assay_ontology_id: d.assay_ontology_id ?? '',
    is_authors_same_as_deposition: d.is_authors_same_as_deposition ?? true,
    authors: (d.authors_json ?? []).filter(
      (a) => a.full_name?.trim() || a.orcid?.trim() || a.affiliation?.trim(),
    ),
    funding: d.funding ?? [],
    crossRefs: [
      ...splitCsv(d.dataset_publications).map((value): CrossRef => ({ type: 'publication', value })),
      ...splitCsv(d.related_database_entries).map((value): CrossRef => ({ type: 'related_db', value })),
    ],
    sample: {
      sample_type: s.sample_type ?? '',
      organism_name: s.organism_name ?? '',
      organism_taxid: s.organism_taxid ?? null,
      tissue_name: s.tissue_name ?? '',
      tissue_id: s.tissue_id ?? '',
      cell_name: s.cell_name ?? '',
      cell_type_id: s.cell_type_id ?? '',
      cell_strain_name: s.cell_strain_name ?? '',
      cell_strain_id: s.cell_strain_id ?? '',
      cell_component_name: s.cell_component_name ?? '',
      ontology: s.ontology ?? '',
      development_stage_name: s.development_stage_name ?? '',
      development_stage_ontology_id: s.development_stage_ontology_id ?? '',
      disease_name: s.disease_name ?? '',
      disease_ontology_id: s.disease_ontology_id ?? '',
    },
  };
}

const NAV: NavItem[] = [
  { key: 'basic', label: 'Basic details', required: true },
  { key: 'sample', label: 'Sample', required: true },
  { key: 'organism', label: 'Organism', required: true },
  { key: 'bioclass', label: 'Biological classification', required: false },
  { key: 'authors', label: 'Authors', required: true },
  { key: 'funding', label: 'Funding & references', required: true },
];

export function DatasetForm({
  dataset,
  reportSave,
  readOnly: readOnlyProp = false,
}: {
  dataset: Dataset;
  reportSave?: (state: AutoSaveState) => void;
  readOnly?: boolean;
}) {
  const queryClient = useQueryClient();
  const { data: deposition } = useDeposition(dataset.deposition);
  const depositionAuthorCount = deposition?.authors_json?.length;
  const [form, setForm] = useState<FormState>(() => toForm(dataset));
  const readOnly = readOnlyProp || dataset.status !== 'draft';
  const refs = useRef<Record<string, HTMLDivElement | null>>({});
  const [active, setActive] = useState('basic');

  useEffect(() => {
    const ACTIVE_LINE = 140;
    const onScroll = () => {
      let current = NAV[0].key;
      for (const n of NAV) {
        const el = refs.current[n.key];
        if (el && el.getBoundingClientRect().top <= ACTIVE_LINE) current = n.key;
      }
      setActive(current);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const save = useCallback(
    async (payload: FormState) => {
      const { crossRefs, authors, ...rest } = payload;
      const csv = (t: CrossRef['type']) =>
        crossRefs.filter((r) => r.type === t).map((r) => r.value.trim()).filter(Boolean).join(', ');
      const updated = await updateDataset(dataset.id, {
        ...rest,
        authors_json: authors,
        dataset_publications: csv('publication'),
        related_database_entries: csv('related_db'),
      });
      queryClient.setQueryData(depositionKeys.dataset(dataset.id), updated);
      queryClient.invalidateQueries({ queryKey: [...depositionKeys.all, 'submissions'] });
    },
    [dataset.id, queryClient],
  );

  const { status, lastSavedAt, saveNow } = useDraftAutoSave(form, save, { enabled: !readOnly });
  useEffect(() => {
    reportSave?.({ status, lastSavedAt, saveNow });
  }, [status, lastSavedAt, saveNow, reportSave]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));
  const setSample = <K extends keyof DatasetSample>(key: K, value: DatasetSample[K]) =>
    setForm((prev) => ({ ...prev, sample: { ...prev.sample, [key]: value } }));

  const setFunding = (i: number, patch: Partial<DatasetFunding>) =>
    set('funding', form.funding.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  const addFunding = () => set('funding', [...form.funding, { funding_agency_name: '', grant_id: '' }]);
  const removeFunding = (i: number) => set('funding', form.funding.filter((_, idx) => idx !== i));

  const addCrossRef = () => set('crossRefs', [...form.crossRefs, { type: 'publication', value: '' }]);

  const hasBio = [
    form.sample.tissue_id,
    form.sample.cell_type_id,
    form.sample.cell_strain_id,
    form.sample.ontology,
    form.sample.development_stage_ontology_id,
    form.sample.disease_ontology_id,
    form.assay_ontology_id,
  ].some(Boolean);
  const done: Record<string, boolean> = {
    basic: !!form.title.trim() && !!form.description.trim(),
    sample: !!form.sample.sample_type,
    organism: !!form.sample.organism_name?.trim() && form.sample.organism_taxid != null,
    bioclass: hasBio,
    authors: true,
    funding: form.funding.length > 0,
  };
  const subLabel = (key: string): string => {
    if (key === 'bioclass') return 'Optional';
    if (key === 'authors') return form.is_authors_same_as_deposition ? 'Deposition authors' : 'Custom';
    if (key === 'funding') return `${form.funding.length} ${form.funding.length === 1 ? 'entry' : 'entries'}`;
    return done[key] ? 'Complete' : 'Incomplete';
  };

  const jump = (key: string) => refs.current[key]?.scrollIntoView({ behavior: 'smooth', block: 'start' });

  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
      <SideNav nav={NAV} active={active} done={done} subLabel={subLabel} onJump={jump} />

      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          bgcolor: 'grey.50',
          borderRadius: 2,
          p: { xs: 2, md: 3 },
          borderLeft: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Stack spacing={3}>
          <BasicDetails
            title={form.title}
            description={form.description}
            onChangeTitle={(v) => set('title', v)}
            onChangeDescription={(v) => set('description', v)}
            readOnly={readOnly}
            innerRef={(el) => {
              refs.current.basic = el;
            }}
          />

          <Sample
            sampleType={form.sample.sample_type ?? ''}
            samplePreparation={form.sample_preparation}
            gridPreparation={form.grid_preparation}
            otherSetup={form.other_setup}
            onChangeSampleType={(v) => setSample('sample_type', v)}
            onChangeSamplePreparation={(v) => set('sample_preparation', v)}
            onChangeGridPreparation={(v) => set('grid_preparation', v)}
            onChangeOtherSetup={(v) => set('other_setup', v)}
            readOnly={readOnly}
            innerRef={(el) => {
              refs.current.sample = el;
            }}
          />

          <Organism
            organismName={form.sample.organism_name ?? ''}
            organismTaxid={form.sample.organism_taxid ?? null}
            onChangeOrganismName={(v) => setSample('organism_name', v)}
            onChangeOrganismTaxid={(v) => setSample('organism_taxid', v)}
            readOnly={readOnly}
            innerRef={(el) => {
              refs.current.organism = el;
            }}
          />

          <BiologicalClassification
            sample={form.sample}
            assayLabel={form.assay_label}
            assayOntologyId={form.assay_ontology_id}
            onChangeSample={setSample}
            onChangeAssayLabel={(v) => set('assay_label', v)}
            onChangeAssayOntologyId={(v) => set('assay_ontology_id', v)}
            readOnly={readOnly}
            innerRef={(el) => {
              refs.current.bioclass = el;
            }}
          />

          <Authors
            sameAsDeposition={form.is_authors_same_as_deposition}
            onChangeSameAsDeposition={(v) => set('is_authors_same_as_deposition', v)}
            depositionAuthorCount={depositionAuthorCount}
            authors={form.authors}
            onChangeAuthors={(a) => set('authors', a)}
            readOnly={readOnly}
            innerRef={(el) => {
              refs.current.authors = el;
            }}
          />

          <Box
            ref={(el: HTMLDivElement | null) => {
              refs.current.funding = el;
            }}
            data-key="funding"
            sx={{ scrollMarginTop: 16 }}
          >
            <Stack spacing={3}>
              <Funding
                funding={form.funding}
                onAdd={addFunding}
                onChange={setFunding}
                onRemove={removeFunding}
                readOnly={readOnly}
                innerRef={() => {}}
              />
              <SectionCard
                title="Cross references"
                sectionKey="crossrefs"
                innerRef={() => {}}
                action={
                  !readOnly ? (
                    <Button sdsType="primary" sdsStyle="minimal" size="small" startIcon={<AddIcon />} onClick={addCrossRef}>
                      Add entry
                    </Button>
                  ) : undefined
                }
              >
                <CrossReferencesEditor
                  entries={form.crossRefs}
                  onChange={(entries) => set('crossRefs', entries)}
                  disabled={readOnly}
                />
              </SectionCard>
            </Stack>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
}
