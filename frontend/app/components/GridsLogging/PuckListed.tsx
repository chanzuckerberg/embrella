'use client';

import React, { useState } from 'react';
import { useGridLoggingPucksByUser } from '@app/common/hooks/useGridLogging/useGridLoggingPuckList';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { 
  Box, 
  Typography,
  Grid,
  Card,
  CardContent,
  CardActionArea,
} from '@mui/material';

interface PuckSelectorProps {
  selectedUser: UsersList | null;
  onPuckSelect: (puck: PucksList | null) => void;
  selectedPuck: PucksList | null;
}

export const PuckListed: React.FC<PuckSelectorProps> = ({
  selectedUser,
  onPuckSelect,
  selectedPuck,
}) => {
  const { pucks, isSuccess } = useGridLoggingPucksByUser(selectedUser?.id);
  console.log('pucks', pucks, selectedUser?.id);
  
  // Extract pucks array from the response object
  const pucksList: PucksList[] = pucks?.pucks || [];

  console.log('pucksList', pucksList);

  // Handle puck selection
  const handlePuckChange = (puckId: string) => {
    const puck = pucksList.find(p => String(p.id) === String(puckId));
    onPuckSelect(puck || null);
  };

  // Handle puck card click
  const handlePuckCardClick = (puck: PucksList) => {
    onPuckSelect(puck);
  };

  if (!selectedUser) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Please select a user first to view their pucks
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Pucks Grid Display */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Available Pucks
        </Typography>
        
        <Grid container spacing={2}>
          {pucksList.map((puck) => (
            <Grid item xs={12} sm={6} md={4} key={puck.id}>
              <Card 
                elevation={selectedPuck?.id === puck.id ? 4 : 1}
                sx={{ 
                  border: selectedPuck?.id === puck.id ? '2px solid #1976d2' : '1px solid #e0e0e0',
                  '&:hover': { 
                    boxShadow: 3,
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out'
                  }
                }}
              >
                <CardActionArea onClick={() => handlePuckCardClick(puck)}>
                  <CardContent sx={{ textAlign: 'center', py: 3 }}>
                    <Typography 
                      variant="h6" 
                      component="div" 
                      sx={{ 
                        fontWeight: 'bold',
                        color: selectedPuck?.id === puck.id ? '#1976d2' : '#333'
                      }}
                    >
                      {puck.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Position in Cane: {puck.position_in_cane} | Max Boxes: {puck.max_boxes}
                    </Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>

        {pucksList.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="text.secondary">
              No pucks available for this user
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};