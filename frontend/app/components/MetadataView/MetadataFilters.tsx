import React, { useState, useEffect } from 'react';
import { Paper, Slider, Typography, TextField } from '@mui/material';
import styles from './MetadataViz.module.css';
import { MiniHistogram } from './MiniHistogram';
import { MetricRanges } from '@app/common/types/metadataViz/metadataVizData';
import { Button } from "@czi-sds/components";

interface MetadataFilterRange {
    current: number;
    min: number;
    max: number;
    histogramData?: number[];
}

type FilterState = {
    [K in keyof MetricRanges]: MetadataFilterRange;
};

interface MetadataFiltersProps {
    metricRanges: MetricRanges;
}

export const MetadataFilters: React.FC<MetadataFiltersProps> = ({ metricRanges }) => {

    console.log(metricRanges,'filtermetric ranges');
    // Initialize state with explicit number conversion
    const [filters, setFilters] = useState<FilterState>(() => {
        const initialState: FilterState = {} as FilterState;
        (Object.keys(metricRanges) as Array<keyof MetricRanges>).forEach(key => {
            initialState[key] = {
                current: Number(metricRanges[key][0]),
                min: Number(metricRanges[key][0]),
                max: Number(metricRanges[key][1])
            };
        });
        return initialState;
    });

    // Update filters when metric ranges change
    useEffect(() => {
        setFilters(prev => {
            const newState = { ...prev };
            (Object.keys(metricRanges) as Array<keyof MetricRanges>).forEach(key => {
                const minVal = Number(metricRanges[key][0]);
                const maxVal = Number(metricRanges[key][1]);
                const currentVal = typeof prev[key]?.current === 'number' ? prev[key].current : minVal;
                
                newState[key] = {
                    ...prev[key],
                    min: minVal,
                    max: maxVal,
                    current: Math.min(Math.max(currentVal, minVal), maxVal)
                };
            });
            return newState;
        });
    }, [metricRanges]);

    const handleSliderChange = (key: keyof FilterState) => (_: Event, newValue: number | number[]) => {
        const value = Number(newValue);
        if (isNaN(value)) return;
        
        setFilters(prev => ({
            ...prev,
            [key]: {
                ...prev[key],
                current: Math.min(Math.max(value, prev[key].min), prev[key].max)
            }
        }));
    };

    const handleReset = () => {
        const resetState: FilterState = {} as FilterState;
        (Object.keys(metricRanges) as Array<keyof MetricRanges>).forEach(key => {
            resetState[key] = {
                current: Number(metricRanges[key][0]),
                min: Number(metricRanges[key][0]),
                max: Number(metricRanges[key][1])
            };
        });
        setFilters(resetState);
    };

    const handleInputChange = (key: keyof FilterState) => (event: React.ChangeEvent<HTMLInputElement>) => {
        const value = Number(event.target.value);
        if (event.target.value === '' || isNaN(value)) return;
        
        setFilters(prev => ({
            ...prev,
            [key]: {
                ...prev[key],
                current: Math.min(Math.max(value, prev[key].min), prev[key].max)
            }
        }));
    };

    const renderFilter = (
        key: keyof FilterState,
        label: string,
        unit: string = '',
        step: number = 1
    ) => {
        const currentValue = Number(filters[key]?.current);
        const minValue = Number(filters[key]?.min);
        const maxValue = Number(filters[key]?.max);
        const stepValue = step || (maxValue - minValue) / 100;  // Dynamic step if not provided

        return (
            <div className={styles.filterRow}>
                <Typography className={styles.filterLabel}>{label} {unit}</Typography>
                <div className={styles.filterContent}>
                    <MiniHistogram />
                    <TextField 
                        size="small" 
                        value={currentValue}
                        className={styles.minMaxInput}
                        onChange={(e) => handleInputChange(key)(e)}
                        inputProps={{ 
                            className: styles.input,
                            type: 'number',
                            min: minValue,
                            max: maxValue,
                            step: stepValue
                        }}
                    />
                    <Slider 
                        value={currentValue}
                        onChange={handleSliderChange(key)}
                        min={minValue}
                        max={maxValue}
                        step={stepValue}
                        className={styles.slider}
                        valueLabelDisplay="auto"
                    />
                    <TextField 
                        size="small" 
                        value={maxValue}
                        className={styles.minMaxInput}
                        inputProps={{ 
                            className: styles.input,
                            type: 'number',
                            readOnly: true 
                        }}
                    />
                </div>
            </div>
        );
    };

    return (
        <Paper className={styles.filterPaper} elevation={1}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h1" gutterBottom>Filters</Typography>
                <Button 
                    sdsType="primary" 
                    sdsStyle="rounded" 
                    onClick={handleReset}
                >
                    Reset
                </Button>
            </div>
            
            {renderFilter('thickness_pix', 'Thickness', '(A)')}
            {renderFilter('tilt_axis', 'Tilt axis', '(°)')}
            {renderFilter('global_shift_pix', 'Global shift')}
            {renderFilter('bad_patch_low', 'Bad patch', '(%)', 0.1)}
            {renderFilter('ctf_resolution_a', 'CTF Resolution')}
            {renderFilter('ctf_score', 'CTF CC Score', '', 0.1)}
        </Paper>
    );
};