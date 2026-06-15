'use client';
import React, { useCallback, useMemo } from 'react';
import JsonView from '@uiw/react-json-view';
import { monokaiTheme } from '@uiw/react-json-view/monokai';
import styles from './MetadataViz.module.css';
import { Card, CardHeader, SelectChangeEvent } from '@mui/material';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';

// Import components and hooks from separate files
import { ActionButtons } from './jsonReport/ActionButtons';
import { SortControls } from './jsonReport/SortControls';
import { useSortedData } from '@app/common/hooks/useFetchMetadata/useRawJsonSortedData';
import { createFocusedJson } from './jsonReport/jsonFormatter';

interface RawJsonProps {
  isOpen: boolean;
  onClose: () => void;
  data?: MetadataVizResponse;
  onSortChange?: (sortBy: string, sortDirection: 'asc' | 'desc') => void;
}

/**
 * Component for displaying raw JSON data with sorting capabilities
 */
export const RawJson: React.FC<RawJsonProps> = ({ isOpen, onClose, data, onSortChange }) => {
  // Use custom hook for sorting state and data fetching with optimizations
  const { sortEnabled, setSortEnabled, sortBy, setSortBy, sortDirection, setSortDirection, sortedData, isLoading } =
    useSortedData(data, onSortChange);

  // Create a JSON representation with accepted position names and filtering ranges
  const jsonData = useMemo(() => {
    return createFocusedJson(sortedData, sortEnabled, sortBy, sortDirection);
  }, [sortedData, sortEnabled, sortBy, sortDirection]);

  // Event handlers with useCallback to prevent unnecessary re-renders
  const handleCopy = useCallback(() => {
    const jsonString = JSON.stringify(jsonData, null, 2);
    navigator.clipboard.writeText(jsonString);
  }, [jsonData]);

  const handleDownload = useCallback(() => {
    const jsonString = JSON.stringify(jsonData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Metadata.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [jsonData]);

  const handleSortToggle = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setSortEnabled(event.target.checked);
    },
    [setSortEnabled]
  );

  const handleSortByChange = useCallback(
    (event: SelectChangeEvent) => {
      setSortBy(event.target.value);
    },
    [setSortBy]
  );

  const handleSortDirectionToggle = useCallback(
    (newDirection: 'asc' | 'desc') => {
      setSortDirection(newDirection);
    },
    [setSortDirection]
  );

  return (
    <div className={`${styles.sidebar} ${isOpen ? styles.open : ''}`}>
      <div className={styles.sidebarContent}>
        <Card elevation={2}>
          <CardHeader
            title="Raw JSON"
            sx={{
              backgroundColor: '#f5f5f5',
              borderBottom: '1px solid #e0e0e0',
            }}
            action={
              <ActionButtons
                sortEnabled={sortEnabled}
                onSortToggle={handleSortToggle}
                onCopy={handleCopy}
                onDownload={handleDownload}
                onClose={onClose}
              />
            }
          />

          {/* Sort controls row - only visible when sorting is enabled */}
          {sortEnabled && (
            <SortControls
              sortEnabled={sortEnabled}
              sortBy={sortBy}
              sortDirection={sortDirection}
              onSortToggle={handleSortToggle}
              onSortByChange={handleSortByChange}
              onSortDirectionToggle={handleSortDirectionToggle}
            />
          )}

          <div className={styles.jsonContainer}>
            {isLoading ? (
              <div style={{ padding: 15, textAlign: 'center' }}>Loading...</div>
            ) : (
              <JsonView
                value={jsonData}
                displayDataTypes={false}
                enableClipboard={false}
                collapsed={1}
                style={{ ...monokaiTheme, padding: 15 }}
              />
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
