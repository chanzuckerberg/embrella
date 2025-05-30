import React from 'react';
import { Slider, Typography, TextField, FormControlLabel, Checkbox } from '@mui/material';
import styles from '../MetadataViz.module.css';
import { getStepValue } from '../utils/FilterUtils';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';
import { FilterState, MetadataFilterRange } from '@app/common/types/metadataViz/FilterType';
import { MetricConfigItem } from '../constants/MetricConfig';

interface FilterItemProps {
  metricKey: keyof FilterState;
  filter: MetadataFilterRange;
  config: MetricConfigItem;
  inputValues?: { min: string; max: string };
  summaryAPIData?: MetadataSummaryResponse;
  onSliderChange: (event: Event, newValue: number | number[]) => void;
  onCheckboxChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onInputChange: (key: keyof FilterState, isMin: boolean) => (event: React.ChangeEvent<HTMLInputElement>) => void;
  onInputBlur: (key: keyof FilterState, isMin: boolean) => () => void;
}

export const FilterItem: React.FC<FilterItemProps> = ({
  metricKey,
  filter,
  config,
  inputValues,
  summaryAPIData,
  onSliderChange,
  onCheckboxChange,
  onInputChange,
  onInputBlur,
}) => {
  const minValue = Number(filter?.min ?? 0);
  const maxValue = Number(filter?.max ?? 100);
  const current = filter?.current ?? [minValue, maxValue];
  const currentMin = Number(current[0].toFixed(3));
  const currentMax = Number(current[1].toFixed(3));
  const stepValue = getStepValue(metricKey as string, minValue, maxValue);

  // Only show median markers for tilt_axis and global_shift
  const showMedian = metricKey === 'tilt_axis' || metricKey === 'global_shift';
  let medianValue;

  if (showMedian && summaryAPIData?.computed_metrics) {
    // Direct mapping to API response names
    const metricName = metricKey === 'tilt_axis' ? 'Tilt Axis' : 'Global Shift';
    // Find the metric in the array
    const metric = summaryAPIData.computed_metrics.find((m) => m.name.includes(metricName));
    medianValue = metric?.median;
  }

  // Create marks for slider if median exists
  const marks = [];
  if (medianValue !== undefined && medianValue >= minValue && medianValue <= maxValue) {
    marks.push({ value: medianValue, label: `Median:${medianValue.toFixed(2)}`, className: styles.medianMarker });
  }

  // Custom styles for the Slider component to style the median marker
  const sliderStyles = {
    // Style for the mark label
    '& .MuiSlider-markLabel': {
      color: '#1976d2',
      fontWeight: 'bold',
      padding: '4px 8px',
      borderRadius: '4px',
      border: '1px solid #1976d2',
      left: '43% !important',
      transform: 'translateX(-50%) !important',
      whiteSpace: 'nowrap',
      marginTop: '-6px',
    },
    // Style for the mark dot
    '& .MuiSlider-mark': {
      backgroundColor: '#1976d2',
      height: '25px',
      width: '3px',
      marginTop: '-9px',
    },
  };

  const renderInputField = (value: number, isMin: boolean) => {
    // Get the current input value from state or use the provided value
    const inputValue =
      inputValues?.[isMin ? 'min' : 'max'] !== undefined ? inputValues[isMin ? 'min' : 'max'] : value.toFixed(3);

    return (
      <TextField
        size="small"
        value={inputValue}
        className={styles.minMaxInput}
        onChange={(e) => onInputChange(metricKey, isMin)(e as React.ChangeEvent<HTMLInputElement>)}
        onBlur={onInputBlur(metricKey, isMin)}
        inputProps={{
          className: styles.input,
          min: minValue,
          max: maxValue,
          step: stepValue,
        }}
      />
    );
  };

  return (
    <div className={styles.filterRow}>
      <FormControlLabel
        control={<Checkbox checked={filter?.enabled} onChange={onCheckboxChange} />}
        label={
          <Typography className={styles.filterLabel}>
            {config?.label} {config?.unit}
          </Typography>
        }
      />
      <div className={styles.filterContent}>
        {renderInputField(currentMin, true)}
        <Slider
          value={[currentMin, currentMax]}
          onChange={onSliderChange}
          min={minValue}
          max={maxValue}
          step={stepValue}
          className={styles.slider}
          disabled={!filter?.enabled}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => value.toFixed(3)}
          marks={marks}
          sx={sliderStyles}
        />
        {renderInputField(currentMax, false)}
      </div>
    </div>
  );
};
