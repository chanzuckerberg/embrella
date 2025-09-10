'use client';

import React from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  Typography,
} from '@mui/material';

interface PuckDetailsProps {
  selectedPuck: PucksList | null;
}

export const PuckDetails: React.FC<PuckDetailsProps> = ({
  selectedPuck,
}) => {
  if (!selectedPuck) {
    return null;
  }

  return (
    <Card elevation={2} sx={{ maxWidth: 600, width: '100%' }}>
      <CardHeader title={`Puck Details: ${selectedPuck.name}`} />
      <CardContent>
        <Typography variant="h4" sx={{ textAlign: 'center', py: 4 }}>
          Hello! This is the puck details screen.
        </Typography>
        <Typography variant="body1" sx={{ textAlign: 'center', mb: 3 }}>
          Selected Puck: {selectedPuck.name}
        </Typography>
      </CardContent>
    </Card>
  );
};