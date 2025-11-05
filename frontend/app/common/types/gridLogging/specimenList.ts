/**
 * Types for Specimen API responses
 */

export interface Sample {
    id: number;
    name: string;
    ontology: string;
  }
  
  export interface Specimen {
    id: number;
    samples: Sample[];
    notes: string;
    notes_page: number | null;
    notes_page_url: string | null;
    display_name: string;
  }
  
  export interface SpecimenListResponse {
    total_specimens_count: number;
    results?: Specimen[];
    specimens?: Specimen[]; // For non-paginated responses
  }
  
  /**
   * Transform specimen data for UI display if needed
   */
  export const transformSpecimen = (specimen: Specimen) => {
    return {
      ...specimen,
      sampleNames: specimen.samples.map(s => s.name).join(', '),
      label: specimen.display_name,
      value: specimen.id,
    };
  };