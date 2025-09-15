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
  Button,
} from '@mui/material';
import { PuckSVG } from './PuckSvg';

interface PuckSelectorProps {
  selectedUser: UsersList | null;
  onPuckSelect: (puck: PucksList | null) => void;
  selectedPuck: PucksList | null;
  onAddPuck?: () => void;
}

export const PuckListed: React.FC<PuckSelectorProps> = ({
  selectedUser,
  onPuckSelect,
  selectedPuck,
  onAddPuck,
}) => {
  const { pucks, isSuccess } = useGridLoggingPucksByUser(selectedUser?.id);
  const pucksList: PucksList[] = pucks?.pucks || [];

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
      {/* Header with Add Puck Button */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        mb: 3 
      }}>
        <Typography variant="h6">
          Pucks
        </Typography>
        {onAddPuck && (
          <Button
            variant="contained"
            startIcon={<span style={{ fontSize: '18px' }}>+</span>}
            onClick={onAddPuck}
            sx={{
              backgroundColor: '#20b2aa',
              '&:hover': {
                backgroundColor: '#1a9b94',
              },
            }}
          >
            Add puck
          </Button>
        )}
      </Box>

      {/* Pucks Grid Display with Interactive SVG */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={3} justifyContent="center">
          {pucksList.map((puck) => (
            <Grid item key={puck.id}>
              <Card 
                elevation={selectedPuck?.id === puck.id ? 4 : 1}
                sx={{ 
                  border: selectedPuck?.id === puck.id ? '2px solid #1976d2' : '1px solid #e0e0e0',
                  borderRadius: '12px',
                  overflow: 'visible',
                  '&:hover': { 
                    boxShadow: 3,
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out'
                  }
                }}
              >
                <CardActionArea onClick={() => handlePuckCardClick(puck)}>
                  <CardContent sx={{ 
                    textAlign: 'center', 
                    py: 3,
                    px: 2,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center'
                  }}>
                    <PuckSVG 
                      puck={puck}
                      size={180}
                      isSelected={selectedPuck?.id === puck.id}
                      disableSlotClick={true}
                    />
                    <Typography 
                      variant="caption" 
                      color="text.secondary" 
                      sx={{ mt: 1, display: 'block' }}
                    >
                       CZII-{puck.name} | Position in Cane: {puck.position_in_cane} 
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