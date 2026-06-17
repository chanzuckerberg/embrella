import React, { useEffect, useState } from 'react';
import { ButtonDropdown, Button, Alert } from '@czi-sds/components';
import { SummaryTable } from './sessionSummary/SummaryTable';
import styles from './MetadataViz.module.css';
import { RawJson } from './RawJson';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';

interface MetadataSummaryProps {
  isFilterApplied?: boolean;
  filteredData?: MetadataVizResponse;
  summaryAPIData?: MetadataSummaryResponse;
  summaryError?: { status: number; message: string };
  summaryLoading?: boolean;
  summarySuccess?: boolean;
  onToggleSummary?: () => void;
}

export const MetadataSummary: React.FC<MetadataSummaryProps> = ({
  isFilterApplied,
  filteredData,
  summaryAPIData,
  summaryError,
  summaryLoading,
  summarySuccess,
  onToggleSummary,
}) => {
  const [showSummary, setShowSummary] = useState(false);
  const [showError, setShowError] = useState(true);
  const [isJsonViewOpen, setIsJsonViewOpen] = useState(false);

  // Determine if we should show the Generate JSON button - only based on filter status and data availability
  const shouldShowGenerateJson = isFilterApplied && filteredData;

  const handleToggleSummary = () => {
    if (!showSummary && onToggleSummary) {
      onToggleSummary();
    }
    setShowSummary(!showSummary);
  };

  const handleToggleJsonView = () => {
    setIsJsonViewOpen(!isJsonViewOpen);
  };

  useEffect(() => {
    if (summaryError) {
      setShowError(true);
    }
  }, [summaryError]);

  const renderContent = () => {
    if (showSummary) {
      if (summaryLoading) return <div className="p-4">Loading...</div>;
      return summaryAPIData && <SummaryTable data={summaryAPIData} />;
    }
    if (summaryError && showError) {
      return (
        <div className={styles.alertContainer}>
          <Alert severity="error" onClose={() => setShowError(false)}>
            {summaryError.status === 404
              ? 'Required files not found. Please check if the session and run number are correct.'
              : summaryError.status === 500
                ? 'Server error occurred. Please try again later'
                : summaryError.message || 'An error occurred while fetching metadata'}
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
            sdsStyle="solid"
            onClick={() => handleToggleSummary()}
            disabled={summaryLoading && !summarySuccess}
          >
            {showSummary ? 'Hide Session Summary' : 'Show Session Summary'}
          </ButtonDropdown>
          {shouldShowGenerateJson && (
            <Button sdsType="primary" sdsStyle="solid" onClick={handleToggleJsonView} className={styles.generateButton}>
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
