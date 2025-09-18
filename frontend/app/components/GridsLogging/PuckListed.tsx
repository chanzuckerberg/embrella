'use client';

import React from 'react';
import { useGridLoggingPucksByUser } from '@app/common/hooks/useGridLogging/useGridLoggingPuckList';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { Box, Typography, Grid, Card, CardContent, CardActionArea } from '@mui/material';
import { PuckSVG } from './PuckSvg';
import styles from './GridLogging.module.css';

interface PuckSelectorProps {
  selectedUser: UsersList | null;
  onPuckSelect: (puck: PucksList | null) => void;
  selectedPuck: PucksList | null;
  _onAddPuck?: () => void;
}

export const PuckListed: React.FC<PuckSelectorProps> = ({ selectedUser, onPuckSelect, selectedPuck, _onAddPuck }) => {
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
      <Box>
        <Grid container spacing={2} justifyContent="flex-start">
          {pucksList.map((puck) => (
            <Grid item key={puck.id} xs={12} sm={6} md={4}>
              <Card
                elevation={selectedPuck?.id === puck.id ? 4 : 1}
                className={`${styles.puckCard} ${selectedPuck?.id === puck.id ? styles.selected : styles.unselected}`}
              >
                <CardActionArea onClick={() => handlePuckCardClick(puck)}>
                  <CardContent className={styles.puckCardContent}>
                    <PuckSVG puck={puck} size={110} isSelected={selectedPuck?.id === puck.id} disableSlotClick={true} />
                    <Typography color="text.secondary">CZII-{puck.name}</Typography>
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
