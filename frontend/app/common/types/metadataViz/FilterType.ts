import { FilterConfig } from '@app/common/types/metadataViz/metadataVizData';

export interface MetadataFilterRange {
  current: [number, number];
  min: number;
  max: number;
  enabled: boolean; // checkbox state
  histogramData?: number[];
}

export type FilterState = {
  [K in keyof FilterConfig['filters']]: MetadataFilterRange;
};
