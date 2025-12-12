import { Sample } from './sampleList';

export interface Specimen {
  id: number;
  samples: Sample[];
  notes: string;
  notes_page: number | null;
  notes_page_url?: string | null;
  display_name?: string;
  name?: string;
}

export interface CreateSampleData {
  name: string;
  ontology?: string;
}

export interface SampleCreateResponse {
  message: string;
  sample: Sample;
}

export interface CreateSpecimenData {
  notes?: string;
  notes_page?: number | null;
  sample_ids?: number[];
}

export interface SpecimenCreateResponse {
  message: string;
  specimen: Specimen;
}

export interface SpecimenListResponse {
  total_specimens_count: number;
  results?: Specimen[];
  specimens?: Specimen[];
}

export const transformSpecimen = (specimen: Specimen) => {
  return {
    ...specimen,
    label: specimen.display_name || `Specimen #${specimen.id}`,
    value: specimen.id,
  };
};
