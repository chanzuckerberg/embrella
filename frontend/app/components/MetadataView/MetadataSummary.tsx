import React, { useEffect, useState } from 'react';
import {
  Button,
  ButtonDropdown,
  Alert
} from "@czi-sds/components";
import { useFetchMetadataSummary } from "@app/common/hooks/useFetchMetadata/useFetchMetadataSummary";
import { SummaryTable } from './summaryTable';
import styles from './MetadataViz.module.css';

interface MetadataSummaryProps {
  sessionName: string;
  runNumber: string;
}

export const MetadataSummary: React.FC<MetadataSummaryProps> = ({ sessionName, runNumber }) => {
  const [showSummary, setShowSummary] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [shouldFetchData, setShouldFetchData] = useState(false);
  const [showError, setShowError] = useState(true);
  const { data, isSuccess, error } = useFetchMetadataSummary(sessionName, runNumber, shouldFetchData);

  const handleToggleSummary = () => {
    if (!showSummary) {
      setShouldFetchData(true);
    } 
    setShowSummary(!showSummary);
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
          <Alert 
            severity="error"
            onClose={() => setShowError(false)}
          >
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
            onClick={handleToggleSummary}
            disabled={isLoading && !isSuccess}
          >
            {showSummary ? 'Hide Summary' : 'Show Summary'}
          </ButtonDropdown>
          <Button 
            sdsType="primary" 
            sdsStyle="rounded" 
            onClick={() => {}}
            className={styles.generateButton}
          >
            Generate Json
          </Button>
        </div>
      </div>
      {renderContent()}
    </div>
  );
};