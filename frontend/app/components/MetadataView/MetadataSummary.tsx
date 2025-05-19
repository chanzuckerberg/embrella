import React, { useEffect, useState } from 'react';
import { ButtonDropdown, Button, Alert } from '@czi-sds/components';
import { useFetchMetadataSummary } from '@app/common/hooks/useFetchMetadata/useFetchMetadataSummary';
import { SummaryTable } from './summaryTable';
import styles from './MetadataViz.module.css';
import { RawJson } from './RawJson';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';

interface MetadataSummaryProps {
  sessionName: string;
  runNumber: string;
  isFilterApplied?: boolean;
  filteredData?: MetadataVizResponse;
}

export const MetadataSummary: React.FC<MetadataSummaryProps> = ({
  sessionName,
  runNumber,
  isFilterApplied = false,
  filteredData,
}) => {
  const [showSummary, setShowSummary] = useState(false);
  const [isLoading] = useState(false);
  const [shouldFetchData, setShouldFetchData] = useState(false);
  const [showError, setShowError] = useState(true);
  const [isJsonViewOpen, setIsJsonViewOpen] = useState(false);
  const { data, isSuccess, error } = useFetchMetadataSummary(sessionName, runNumber, shouldFetchData);

  // Determine if we should show the Generate JSON button - only based on filter status and data availability
  const shouldShowGenerateJson = isFilterApplied && filteredData;

  const handleToggleSummary = () => {
    if (!showSummary) {
      setShouldFetchData(true);
    }
    setShowSummary(!showSummary);
  };

  const handleToggleJsonView = () => {
    setIsJsonViewOpen(!isJsonViewOpen);
  };

  useEffect(() => {
    if (error) {
      setShowError(true);
    }
  }, [error]);

  const renderContent = () => {
    if (showSummary) {
      if (isLoading) return <div className="p-4">Loading...</div>;
      return data && <SummaryTable data={data} />;
    }
    if (error && showError) {
      return (
        <div className={styles.alertContainer}>
          <Alert severity="error" onClose={() => setShowError(false)}>
            {error.status === 404
              ? 'Required files not found. Please check if the session and run number are correct.'
              : error.status === 500
                ? 'Server error occurred. Please try again later'
                : error.message || 'An error occurred while fetching metadata'}
          </Alert>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full">
      <div className={styles.headerContainer}>
        <div className={styles.buttonGroup}>
          <ButtonDropdown
            sdsType="primary"
            sdsStyle="rounded"
            onClick={() => handleToggleSummary()}
            disabled={isLoading && !isSuccess}
          >
            {showSummary ? 'Hide Session Summary' : 'Show Session Summary'}
          </ButtonDropdown>
          {shouldShowGenerateJson && (
            <Button
              sdsType="primary"
              sdsStyle="rounded"
              onClick={handleToggleJsonView}
              className={styles.generateButton}
            >
            Generate Json
            </Button>
          )}
          <RawJson isOpen={isJsonViewOpen} onClose={() => setIsJsonViewOpen(false)} data={filteredData} />
        </div>
      </div>
      {renderContent()}
    </div>
  );
};
