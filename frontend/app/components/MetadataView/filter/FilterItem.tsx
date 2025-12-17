import React, { memo, useMemo, useCallback } from 'react';
import { Slider, Typography, FormControlLabel, Checkbox, TextField } from '@mui/material';
import styles from '../MetadataViz.module.css';
import { getStepValue } from '../utils/FilterUtils';
import { FilterState } from '@app/common/types/metadataViz/FilterType';
import { MetricConfigItem } from '../constants/MetricConfig';

interface FilterItemProps {
  metricKey: keyof FilterState;
  filter: {
    current: [number, number];
    min: number;
    max: number;
    enabled: boolean;
  };
  config: MetricConfigItem;
  inputValues?: { min: string; max: string };
  medianValue?: { value: number | undefined; hasMedian: boolean };
  onSliderChange: (event: Event, newValue: number | number[]) => void;
  onCheckboxChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onInputChange: (key: keyof FilterState, isMin: boolean) => (event: React.ChangeEvent<HTMLInputElement>) => void;
  onInputBlur: (key: keyof FilterState, isMin: boolean) => () => void;
}

export const FilterItem: React.FC<FilterItemProps> = memo(
  ({
    metricKey,
    filter,
    config,
    inputValues,
    medianValue,
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

    // Create marks for slider if median exists - memoize to prevent recalculation
    const marks = useMemo(() => {
      const result = [];
      if (
        medianValue?.hasMedian &&
        medianValue.value !== undefined &&
        medianValue.value >= minValue &&
        medianValue.value <= maxValue
      ) {
        result.push({
          value: medianValue.value,
          label: `Median:${medianValue.value.toFixed(2)}`,
          className: styles.medianMarker,
        });
      }
      return result;
    }, [medianValue, minValue, maxValue]);

    // Custom styles for the Slider component to style the median marker
    const sliderStyles = {
      // Style for the mark label
      '& .MuiSlider-markLabel': {
        color: '#6E4FF9',
        fontWeight: 'bold',
        padding: '4px 8px',
        borderRadius: '4px',
        border: '1px solid #6E4FF9',
        left: '43% !important',
        transform: 'translateX(-50%) !important',
        whiteSpace: 'nowrap',
        marginTop: '-6px',
      },
      // Style for the mark dot
      '& .MuiSlider-mark': {
        backgroundColor: '#6E4FF9',
        height: '25px',
        width: '3px',
        marginTop: '-9px',
      },
    };

    // Memoize the input change handlers to prevent recreating them on each render
    const handleMinInputChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => onInputChange(metricKey, true)(e),
      [metricKey, onInputChange]
    );

    const handleMaxInputChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => onInputChange(metricKey, false)(e),
      [metricKey, onInputChange]
    );

    const handleMinInputBlur = useCallback(() => onInputBlur(metricKey, true)(), [metricKey, onInputBlur]);

    const handleMaxInputBlur = useCallback(() => onInputBlur(metricKey, false)(), [metricKey, onInputBlur]);

    const renderInputField = (value: number, isMin: boolean) => {
      // Get the current input value from state or use the provided value
      const inputValue =
        inputValues?.[isMin ? 'min' : 'max'] !== undefined ? inputValues[isMin ? 'min' : 'max'] : value.toFixed(3);

      return (
        <TextField
          size="small"
          value={inputValue}
          className={styles.minMaxInput}
          onChange={isMin ? handleMinInputChange : handleMaxInputChange}
          onBlur={isMin ? handleMinInputBlur : handleMaxInputBlur}
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
  }
);

FilterItem.displayName = 'FilterItem';
