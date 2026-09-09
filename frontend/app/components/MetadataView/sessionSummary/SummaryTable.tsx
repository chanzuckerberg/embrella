import React from 'react';
import { Card, CardContent, Divider, Typography, Paper, Box } from '@mui/material';
import { MetadataSummaryResponse } from '@app/common/types/metadataViz/metadataSummary';
import { MetricsTable } from './MetricsTable';

interface SummaryTableProps {
  data: MetadataSummaryResponse;
}

// Component for displaying a single info item with label and value
interface InfoItemProps {
  label: string;
  value: string | number | null;
  breakWord?: boolean;
}

const InfoItem: React.FC<InfoItemProps> = ({ label, value, breakWord = false }) => (
  <Typography variant="body1" sx={{ mb: 1, ...(breakWord && { wordBreak: 'break-all' }) }}>
    <strong>{label}:</strong> {value}
  </Typography>
);

// Component for the summary card with session information
interface SummaryCardProps {
  data: MetadataSummaryResponse;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ data }) => (
  <Card elevation={2} sx={{ mb: 3 }}>
    <CardContent>
      <Box>
        <InfoItem label="Session" value={data.session_name} />
        <InfoItem label="Run" value={data.run_number} />
        <InfoItem label="Total number of Tomograms" value={data.num_tomograms} />
        <InfoItem label="Tilt Series Pixel Size (Å)" value={data.pixel_size} />
        <InfoItem label="User" value={data.user_name} />
        <InfoItem label="Project" value={data.project_name} />
        <InfoItem label="Grid" value={data.grid_name} />
      </Box>

      <Divider sx={{ my: 3 }} />

      <Box>
        <InfoItem label="Data Collection Path" value={data.data_collection_directory} breakWord={true} />
        <InfoItem label="Aretomo3 Processing Path" value={data.aretomo3_processing_directory} breakWord={true} />
      </Box>
    </CardContent>
  </Card>
);

// Main SummaryTable component
export const SummaryTable: React.FC<SummaryTableProps> = ({ data }) => {
  if (!data) {
    return <Typography variant="body1">No data available</Typography>;
  }

  return (
    <Box sx={{ marginTop: 4 }}>
      <Paper
        sx={{
          p: 3,
          bgcolor: 'background.paper',
          borderRadius: 1,
          mt: 1,
          boxShadow: 'none', // Remove shadow to eliminate the line
          border: 'none',
        }}
      >
        <SummaryCard data={data} />

        {data.computed_metrics && data.computed_metrics.length > 0 ? (
          <MetricsTable metrics={data.computed_metrics} />
        ) : (
          <Typography variant="body1">No metrics data available</Typography>
        )}
      </Paper>
    </Box>
  );
};
