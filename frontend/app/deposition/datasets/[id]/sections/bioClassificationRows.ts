import { GO_CELLULAR_COMPONENT_IRI } from '../../../services/ols';
import type { DatasetSample } from '../../../types';

export interface BioRow {
  key: string;
  label: string;
  prefix: string;
  ontology: string;
  pattern: string;
  nameKey: keyof DatasetSample;
  idKey: keyof DatasetSample;
  lookup: string;
  manualOnly?: boolean;
  idPlaceholder?: string;
  /** Restrict OLS suggestions */
  childrenOf?: string;
  description: string;
}

export const BIO_ROWS: BioRow[] = [
  {
    key: 'tissue',
    label: 'Tissue',
    prefix: 'UBERON',
    ontology: 'uberon,cl,bto,fbbt,wbbt,zfa',
    pattern: '(^BTO:[0-9]{7}$)|(^CL:[0-9]{7}$)|(WBbt:[0-9]{7}$)|(ZFA:[0-9]{7}$)|(FBbt:[0-9]{8}$)|(^UBERON:[0-9]{7}$)',
    nameKey: 'tissue_name',
    idKey: 'tissue_id',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/uberon',
    description: 'The tissue or anatomical structure the sample came from',
  },
  {
    key: 'cell_type',
    label: 'Cell type',
    prefix: 'CL',
    ontology: 'cl,uberon,fbbt,wbbt,zfa',
    pattern: '(^CL:[0-9]{7}$)|(WBbt:[0-9]{7}$)|(ZFA:[0-9]{7}$)|(FBbt:[0-9]{8}$)|(^UBERON:[0-9]{7}$)',
    nameKey: 'cell_name',
    idKey: 'cell_type_id',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/cl',
    description: 'The kind of cell imaged (e.g. neuron, T cell)',
  },
  {
    // Not in OLS - manual id entry (format-validated) + Cellosaurus lookup.
    key: 'cell_strain',
    label: 'Cell strain',
    prefix: 'CVCL',
    ontology: '',
    pattern: '(WBStrain[0-9]{8}$)|(^NCBITaxon:[0-9]+$)|(^CVCL_[A-Z0-9]{4,}$)|(^CC-[0-9]{4}$)',
    manualOnly: true,
    idPlaceholder: 'e.g. CVCL_1234, NCBITaxon:562, CC-0012',
    nameKey: 'cell_strain_name',
    idKey: 'cell_strain_id',
    lookup: 'https://www.cellosaurus.org',
    description: 'A specific cell line or strain (e.g. HeLa)',
  },
  {
    key: 'cell_component',
    label: 'Cell component',
    prefix: 'GO',
    ontology: 'go',
    pattern: '^GO:[0-9]{7}$',
    nameKey: 'cell_component_name',
    idKey: 'ontology',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/go',
    childrenOf: GO_CELLULAR_COMPONENT_IRI,
    description: 'The subcellular structure or organelle imaged',
  },
  {
    key: 'development_stage',
    label: 'Development stage',
    prefix: 'UBERON',
    ontology: 'uberon,hsapdv,mmusdv,zfs,fbdv',
    pattern:
      '(^unknown$)|(WBls:[0-9]{7}$)|(^UBERON:[0-9]{7}$)|(HsapDv:[0-9]{7}$)|(MmusDv:[0-9]{7}$)|(ZFS:[0-9]{7}$)|(FBdv:[0-9]{8}$)',
    nameKey: 'development_stage_name',
    idKey: 'development_stage_ontology_id',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/uberon',
    description: 'The developmental stage of the organism',
  },
  {
    key: 'disease',
    label: 'Disease',
    prefix: 'MONDO',
    ontology: 'mondo,pato',
    pattern: '(^MONDO:[0-9]{7}$)|(^PATO:[0-9]{7}$)',
    nameKey: 'disease_name',
    idKey: 'disease_ontology_id',
    lookup: 'https://www.ebi.ac.uk/ols4/ontologies/mondo',
    description: 'Any disease or condition associated with the sample',
  },
];
