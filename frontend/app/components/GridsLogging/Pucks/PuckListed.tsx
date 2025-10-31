'use client';

import React from 'react';
import { useGridLoggingPucksByUser } from '@app/common/hooks/useGridLogging/useGridLoggingPuckList';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Box, Typography, Card, CardContent, CardActionArea, Grid } from '@mui/material';
import { PuckSVG } from './PuckSvg';
import styles from '../GridLogging.module.css';

interface PuckSelectorProps {
  selectedUser: UsersList | null;
  onPuckSelect: (puck: PucksList | null) => void;
  selectedPuck: PucksList | null;
}

export const PuckListed: React.FC<PuckSelectorProps> = ({ selectedUser, onPuckSelect, selectedPuck }) => {
  const { pucks } = useGridLoggingPucksByUser(selectedUser?.id);
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
      {/* Pucks Grid Display with Interactive SVG */}
      <Box className={styles.pucksScrollContainer}>
        <Grid container spacing={2} justifyContent="flex-start">
          {pucksList.map((puck) => (
            <Grid
              key={puck.id}
              sx={{
                width: {
                  xs: '100%',
                  sm: 'calc(50% - 8px)',
                  md: 'calc(33.333% - 8px)',
                  margin: '3px',
                  marginTop: '8px',
                  marginLeft: '5px',
                },
                maxWidth: { xs: '100%', sm: 'calc(50% - 8px)', md: 'calc(33.333% - 8px)' },
              }}
            >
              <Card
                elevation={selectedPuck?.id === puck.id ? 4 : 1}
                className={`${styles.puckCard} ${selectedPuck?.id === puck.id ? styles.selected : styles.unselected}`}
              >
                <CardActionArea onClick={() => handlePuckCardClick(puck)}>
                  <CardContent className={styles.puckCardContent}>
                    <PuckSVG puck={puck} size={110} isSelected={selectedPuck?.id === puck.id} disableSlotClick={true} />
                    <Typography color="text.secondary">CZII-0{puck.name}</Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>

        {pucksList.length === 0 && (
          <Box className={styles.emptyState}>
            <Typography variant="body1" color="text.secondary">
              No pucks available for this user
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};
