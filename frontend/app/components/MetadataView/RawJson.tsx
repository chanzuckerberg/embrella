import React from 'react';
import ReactJson from 'react-json-view';
import styles from './MetadataViz.module.css';
import { Card, CardHeader } from '@mui/material';
import { Icon } from '@czi-sds/components';
import { METRICS_CONFIG } from './constants/MetricConfig';
import { MetadataVizResponse } from '@app/common/types/metadataViz/metadataVizData';

interface RawJsonProps {
  isOpen: boolean;
  onClose: () => void;
  data?: MetadataVizResponse;
}

export const RawJson: React.FC<RawJsonProps> = ({ isOpen, onClose, data }) => {
  // Create a focused JSON representation with position names and filtering ranges
  const createFocusedJson = () => {
    if (!data) return {};

    // Get position names from accepted results
    const positionNames = data.accepted_results?.map((item) => item.name) || [];

    // Get filtering ranges from filters_applied
    const filterRanges: Record<string, string> = {};

    if (data.filters_applied?.filters) {
      // Convert filter ranges to readable format
      Object.entries(data.filters_applied.filters).forEach(([key, range]) => {
        if (Array.isArray(range) && range.length === 2) {
          // Get unit from METRICS_CONFIG
          const unit = METRICS_CONFIG[key as keyof typeof METRICS_CONFIG]?.unit || '';

          // Fix decimal places to 2 for better readability
          const minValue = Number(range[0]).toFixed(2);
          const maxValue = Number(range[1]).toFixed(2);

          filterRanges[key] = `${minValue}-${maxValue}${unit}`;
        }
      });
    }

    return {
      'Selected positions': positionNames,
      'Filtering ranges': filterRanges,
      'Filter type': data.filters_applied?.filter_type || 'None',
    };
  };

  const jsonData = createFocusedJson();

  const handleCopy = () => {
    const jsonString = JSON.stringify(jsonData, null, 2);
    navigator.clipboard.writeText(jsonString);
  };

  const handleDownload = () => {
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
  };

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
              <div style={{ display: 'flex', flexDirection: 'row', gap: '9px' }}>
                <div
                  onClick={() => {
                    handleCopy();
                  }}
                >
                  <Icon color="green" sdsIcon="Copy" sdsSize="s" />
                </div>
                <div
                  onClick={() => {
                    handleDownload();
                  }}
                >
                  <Icon color="green" sdsIcon="Download" sdsSize="s" />
                </div>
                <div
                  onClick={() => {
                    onClose();
                  }}
                >
                  <Icon color="green" sdsIcon="XMark" sdsSize="s" />
                </div>
              </div>
            }
          />
          <div className={styles.jsonContainer}>
            <ReactJson
              src={jsonData}
              theme="monokai"
              displayDataTypes={false}
              enableClipboard={false}
              collapsed={1}
              style={{ padding: 15 }}
            />
          </div>
        </Card>
      </div>
    </div>
  );
};
