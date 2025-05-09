import React, { useState, useEffect } from 'react';
import {
  Paper,
  Slider,
  Typography,
  TextField,
  FormControlLabel,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import styles from './MetadataViz.module.css';
import { MiniHistogram } from './MiniHistogram';
import { MetricRanges } from '@app/common/types/metadataViz/metadataVizData';
import { Button } from '@czi-sds/components';

interface MetadataFilterRange {
  current: [number, number];
  min: number;
  max: number;
  enabled: boolean; //checkbox state
  histogramData?: number[];
}

type FilterState = {
  [K in keyof MetricRanges]: MetadataFilterRange;
};

interface MetadataFiltersProps {
  metricRanges: MetricRanges;
  // onApplyFilters?: (filters: FilterState, selectedOption: string) => void;
}

export const MetadataFilters: React.FC<MetadataFiltersProps> = ({ metricRanges }) => {
  const [selectedOption, setSelectedOption] = useState('AND');

  // Initialize state with explicit number conversion
  const [filters, setFilters] = useState<FilterState>(() => {
    const initialState: FilterState = {} as FilterState;
    (Object.keys(metricRanges) as Array<keyof MetricRanges>).forEach((key) => {
      initialState[key] = {
        current: [Number(metricRanges[key][0]), Number(metricRanges[key][1])],
        min: Number(metricRanges[key][0]),
        max: Number(metricRanges[key][1]),
        enabled: true,
      };
    });
    return initialState;
  });

  // Update filters when metric ranges change
  useEffect(() => {
    setFilters((prev) => {
      const newState = { ...prev };
      (Object.keys(metricRanges) as Array<keyof MetricRanges>).forEach((key) => {
        const minVal = Number(metricRanges[key][0]);
        const maxVal = Number(metricRanges[key][1]);

        newState[key] = {
          ...prev[key],
          min: minVal,
          max: maxVal,
          current: [
            Math.min(Math.max(prev[key]?.current[0] ?? minVal, minVal), maxVal),
            Math.min(Math.max(prev[key]?.current[1] ?? maxVal, minVal), maxVal),
          ],
          enabled: prev[key]?.enabled ?? true,
        };
      });
      return newState;
    });
  }, [metricRanges]);

  const handleSliderChange = (key: keyof FilterState) => (_: Event, newValue: number | number[]) => {
    if (!Array.isArray(newValue)) return;

    setFilters((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        current: [Math.max(newValue[0], prev[key]?.min ?? 0), Math.min(newValue[1], prev[key]?.max ?? 100)],
      },
    }));
  };

  const handleCheckboxChange = (key: keyof FilterState) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        enabled: event.target.checked,
      },
    }));
  };

  const handleReset = () => {
    const resetState: FilterState = {} as FilterState;
    (Object.keys(metricRanges) as Array<keyof MetricRanges>).forEach((key) => {
      resetState[key] = {
        current: [Number(metricRanges[key][0]), Number(metricRanges[key][1])],
        min: Number(metricRanges[key][0]),
        max: Number(metricRanges[key][1]),
        enabled: true,
      };
    });
    setFilters(resetState);
    setSelectedOption('AND');
  };

  const handleInputChange =
    (key: keyof FilterState, isMin: boolean) => (event: React.ChangeEvent<HTMLInputElement>) => {
      const value = Number(event.target.value);
      if (event.target.value === '' || isNaN(value)) return;

      setFilters((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          current: isMin
            ? [Math.min(Math.max(value, prev[key].min), prev[key].current[1]), prev[key].current[1]]
            : [prev[key].current[0], Math.min(Math.max(value, prev[key].current[0]), prev[key].max)],
        },
      }));
    };

  // const handleApplyFilters = () => {
  //   if (onApplyFilters) {
  //     onApplyFilters(filters, selectedOption);
  //   }
  // };
  const renderFilter = (key: keyof FilterState, label: string, unit: string = '', step: number = 1) => {
    const minValue = Number(filters[key]?.min ?? 0);
    const maxValue = Number(filters[key]?.max ?? 100);
    const current = filters[key]?.current ?? [minValue, maxValue];
    const currentMin = current[0];
    const currentMax = current[1];
    const stepValue = step || (maxValue - minValue) / 100;

    return (
      <div className={styles.filterRow}>
        <FormControlLabel
          control={<Checkbox checked={filters[key]?.enabled} onChange={handleCheckboxChange(key)} />}
          label={
            <Typography className={styles.filterLabel}>
              {label} {unit}
            </Typography>
          }
        />
        <div className={styles.filterContent}>
          <MiniHistogram />
          <TextField
            size="small"
            value={currentMin}
            className={styles.minMaxInput}
            onChange={(e) => handleInputChange(key, true)(e as React.ChangeEvent<HTMLInputElement>)}
            inputProps={{
              className: styles.input,
              type: 'number',
              min: minValue,
              max: maxValue,
              step: stepValue,
            }}
          />
          <Slider
            value={[currentMin, currentMax]}
            onChange={handleSliderChange(key)}
            min={minValue}
            max={maxValue}
            step={stepValue}
            className={styles.slider}
            disabled={!filters[key]?.enabled}
            valueLabelDisplay="auto"
          />
          <TextField
            size="small"
            value={currentMax}
            className={styles.minMaxInput}
            onChange={(e) => handleInputChange(key, false)(e as React.ChangeEvent<HTMLInputElement>)}
            inputProps={{
              className: styles.input,
              type: 'number',
              min: minValue,
              max: maxValue,
              step: stepValue,
            }}
          />
        </div>
      </div>
    );
  };

  return (
    <Paper className={styles.filterPaper} elevation={1}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <Typography variant="h1">Filters</Typography>
        <FormControl style={{ minWidth: 100 }}>
          <InputLabel sx={{ backgroundColor: 'white', padding: '0 4px' }}>Filter Type</InputLabel>
          <Select
            label="Filter Type"
            value={selectedOption}
            onChange={(e) => setSelectedOption(e.target.value)}
            size="small"
          >
            <MenuItem value="AND">AND</MenuItem>
            <MenuItem value="OR">OR</MenuItem>
          </Select>
        </FormControl>
      </div>

      {renderFilter('thickness_pix', 'Thickness', '(Pix)')}
      {renderFilter('tilt_axis', 'Tilt axis', '(°)')}
      {renderFilter('global_shift_pix', 'Global shift')}
      {renderFilter('bad_patch_low', 'Bad patch low', '(%)', 0.1)}
      {renderFilter('bad_patch_all', 'Bad patch All', '(%)', 0.1)}
      {renderFilter('ctf_resolution_a', 'CTF Resolution', '(A)')}
      {renderFilter('ctf_score', 'CTF CC Score', '', 0.1)}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
        <Button sdsType="secondary" sdsStyle="rounded" onClick={handleReset}>
          Reset
        </Button>
        <Button
          sdsType="primary"
          sdsStyle="rounded"
          // onClick={handleApplyFilters}
        >
          Apply Filter
        </Button>
      </div>
    </Paper>
  );
};
