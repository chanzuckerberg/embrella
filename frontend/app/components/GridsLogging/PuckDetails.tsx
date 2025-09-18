'use client';

import React from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { PuckSVG } from './PuckSvg';
import { Card, CardContent, CardHeader, Box, IconButton, Typography } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import styles from './GridLogging.module.css';

interface PuckDetailsProps {
  selectedPuck: PucksList | null;
  onAddGridBox: () => void;
  onSlotSelect: (slotPosition: number) => void;
  _selectedSlot: number | null;
}

export const PuckDetails: React.FC<PuckDetailsProps> = ({
  selectedPuck,
  onAddGridBox,
  onSlotSelect,
  _selectedSlot,
}) => {
  const handleSlotClick = (slotPosition: number) => {
    onSlotSelect(slotPosition);
  };

  const handleDeletePuck = () => {
    // Redirect to Django admin puck deletion page
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/puck/${selectedPuck?.id}/delete/`;
    window.open(adminUrl, '_blank');
  };

  if (!selectedPuck) {
    return null;
  }

  return (
    <Card elevation={2} sx={{ maxWidth: 600, width: '100%' }}>
       <CardHeader 
       title={
         <Box className={styles.cardHeader}>
           <Typography variant="h6" component="h2">
             Puck Details: {selectedPuck.name}
           </Typography>
           <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
             <Button
               sdsType="primary"
               sdsStyle="rounded"
               startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
               onClick={onAddGridBox}
               size="small"
             >
               Add Grid Box
             </Button>
             <IconButton onClick={handleDeletePuck}>
               <Icon sdsIcon="TrashCan" sdsSize="xl" color="red" />
             </IconButton>
           </Box>
         </Box>
       }
     />
    
      <CardContent>
        {/* Display the selected puck SVG */}
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 4 }}>
          <PuckSVG puck={selectedPuck} size={290} isSelected={true} onSlotClick={handleSlotClick} />
        </Box>
      </CardContent>
    </Card>
  );
};
