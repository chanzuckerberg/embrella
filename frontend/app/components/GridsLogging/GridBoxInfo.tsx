'use client';

import React, { useState } from 'react';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  Typography, 
  Box, 
  IconButton, 
} from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';
import styles from './GridLogging.module.css';
import Image from 'next/image';

interface GridBoxInfoProps {
  selectedPuck: PucksList | null;
  selectedSlot: number | null;
  onAddGridBox: () => void;
}


export const GridBoxInfo: React.FC<GridBoxInfoProps> = ({ selectedPuck, selectedSlot, onAddGridBox }) => {
  const [gridBoxData, setGridBoxData] = useState({
    name: '',
    color: 'FFFFFF',
    numbering: 'ucw',
    puck: selectedPuck?.name || '',
    maxGrids: 4,
    positionInPuck: selectedSlot || 1,
  });

  if (!selectedPuck || !selectedSlot) {
    return null;
  }

  const handleDeleteGrid = () => {
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/${selectedSlot}/delete/`;
    window.open(adminUrl, '_blank');
    onAddGridBox();
  };

  const handleAddGrid = () => {
    // Redirect to Django admin for adding grid
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryogrid/add/`;
    window.open(adminUrl, '_blank');
  };

  const handleMoveGridBox = () => {
    console.log('Move grid box');
  };

  const handleSave = () => {
    console.log('Save grid box:', gridBoxData);
  };

  return (
    <Card elevation={2} sx={{ maxWidth: 600, width: '100%' }}>
       <CardHeader 
       title={
         <Box className={styles.cardHeader}>
           <Typography variant="h6" component="h2">
             GridBox Information: Puck-{selectedPuck.name}/Slot-{selectedSlot}
           </Typography>
           <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
             <Button
               sdsType="primary"
               sdsStyle="rounded"
               startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
               onClick={handleAddGrid}
               size="small"
             >
               Add Grid
             </Button>
             <IconButton onClick={handleDeleteGrid} sx={{'&:hover': {
                  backgroundColor: '#ffebee',
                },}}>
               <Icon sdsIcon="TrashCan" sdsSize="xl" color="red"/>
             </IconButton>
           </Box>
         </Box>
       }
     />
    
      <CardContent>
        {/* Display the selected GridBox SVG */}
       <Box> 
            <Image
                src="/next/GridBox.svg"
                alt="Grid Box"
                width={200}
                height={150}
                style={{ objectFit: 'contain' }}
            />
        </Box> 
      </CardContent>
    </Card>
  );
};