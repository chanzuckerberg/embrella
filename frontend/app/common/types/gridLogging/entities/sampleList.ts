export interface Sample {
    id: number;
    name: string;
    ontology: string;
  }
export interface SampleListResponse {
    total_samples_count: number;
    results?: Sample[];
    samples?: Sample[];
}
  
export const transformSample = (sample: Sample) => {
    return {
      ...sample,
      label: sample.ontology ? `${sample.name} (${sample.ontology})` : sample.name,
      value: sample.id,
    };
};