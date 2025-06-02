import React, { memo } from 'react';
import { Paper } from '@mui/material';
import styles from './MetadataViz.module.css';
import { MetricRanges } from '@app/common/types/metadataViz/metadataVizData';
import { METRICS_CONFIG } from './constants/MetricConfig';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';
import { FilterHeader } from './filter/FilterHeader';
import { FilterItem } from './filter/FilterItem';
import { FilterControls } from './filter/FilterControls';
import { asMetricKey } from './utils/FilterUtils';
import { UseFilterStateReturn } from '@app/common/hooks/useFetchMetadata/useFilterState';

interface MetadataFiltersProps {
  metricRanges: MetricRanges;
  filterState: UseFilterStateReturn;
  summaryAPIData?: MetadataSummaryResponse;
}

/**
 * Component that renders filter controls for metadata visualization
 * Uses a centralized filter state from the useFilterState hook
 */
export const MetadataFilters: React.FC<MetadataFiltersProps> = memo(({ metricRanges, filterState, summaryAPIData }) => {
  // Destructure the filter state and actions from the provided hook instance
  const {
    filters,
    filterType,
    inputValues,
    medianValues,
    handleSliderChange,
    handleCheckboxChange,
    handleInputChange,
    handleInputBlur,
    handleReset,
    handleApplyFilters,
    handleUncheckAll,
    setFilterType,
  } = filterState;

  return (
    <Paper className={styles.filterPaper} elevation={1}>
      <FilterHeader selectedOption={filterType} onOptionChange={(option) => setFilterType(option)} />

      {Object.keys(filters).map((key) => {
        const metricKey = asMetricKey(key);
        return (
          <FilterItem
            key={`filter-${key}`}
            metricKey={metricKey}
            filter={filters[metricKey]!}
            config={METRICS_CONFIG[metricKey]}
            inputValues={inputValues[metricKey]}
            medianValue={medianValues[metricKey]}
            onSliderChange={handleSliderChange(metricKey)}
            onCheckboxChange={handleCheckboxChange(metricKey)}
            onInputChange={handleInputChange}
            onInputBlur={handleInputBlur}
          />
        );
      })}

      <FilterControls onReset={handleReset} onUncheckAll={handleUncheckAll} onApplyFilters={handleApplyFilters} />
    </Paper>
  );
});
