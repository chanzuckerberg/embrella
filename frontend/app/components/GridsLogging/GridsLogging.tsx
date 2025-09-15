'use client';

import React, { useState, useEffect, useContext } from 'react';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import {  UserContext } from '@app/common/context/UserProvider';
import {  UsersList } from '@app/common/types/gridLogging/userList';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import styles from './GridLogging.module.css';
import { PuckListed } from './PuckListed';
import { PuckDetails } from './PuckDetails';
import { GridBoxInfo } from './GridBoxInfo';
import { 
  Card, 
  CardContent, 
  CardHeader, 
  Box, 
  Select,
  MenuItem,
  FormControl,
} from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { DJANGO_URL } from '@app/common/constants/api';

interface GridsLoggingProps {
  onAddPuck?: () => void;
}

export const GridsLogging: React.FC<GridsLoggingProps> = ({
  onAddPuck,
}) => {

  const [selectedUser, setSelectedUser] = useState<UsersList | null>(null);
  const [selectedPuck, setSelectedPuck] = useState<PucksList | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const { users, isSuccess } = useGridLoggingUserList();
  const currentUser = useContext(UserContext);
  
  // Extract users array from the response object
  const usersList: UsersList[] = users?.users || [];
  
  // Set the current user as default when users are loaded
  useEffect(() => {
    if (usersList.length > 0 && currentUser && !selectedUser) {
      // Find the current user in the users list
      const foundUser = usersList.find(u => String(u.id) === String(currentUser.id));
      if (foundUser) {
        setSelectedUser(foundUser);
      } 
    }
  }, [usersList, currentUser, selectedUser]);

  // Handle user selection
  const handleUserChange = (userId: string) => {
    const user = usersList.find(u => String(u.id) === String(userId));
    setSelectedUser(user || null);
    // Reset selected puck and slot when user changes
    setSelectedPuck(null);
    setSelectedSlot(null);
  };

  const handleAddPuck = () => {
    // Redirect to Django admin puck creation page
    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/puck/add/`;
    window.open(adminUrl, '_blank');
  }
 
  const handlePuckSelect = (puck: PucksList | null) => {
    setSelectedPuck(puck);
    // Reset selected slot when puck changes
    setSelectedSlot(null);
  };

  const handleSlotSelect = (slotPosition: number) => {
    setSelectedSlot(slotPosition);
  };

  const handleCloseSlotDetails = () => {
    setSelectedSlot(null);
  };

  const handleAddGridBox = () => {
    // Add grid box logic
    console.log('Adding grid box to slot:', selectedSlot);
  };

  return (
    <Box className={styles.mainContainer}>
      {/* Top Section - Puck List and Puck Details */}
      <Box className={styles.topSection}>
        <Card elevation={2} className={styles.leftCard}>
          <CardHeader title="Pucks" />
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 4, flexGrow: 1 }}>
              <FormControl variant="outlined" size="small" sx={{ minWidth: 300 }}>
                <Select
                  value={selectedUser?.id || ''}
                  onChange={(e) => handleUserChange(String(e.target.value))}
                  displayEmpty
                >
                  <MenuItem value="" disabled><em>Select User</em></MenuItem>
                  {usersList.map((user) => (
                    <MenuItem key={user.id} value={String(user.id)}>
                      {user.full_name || user.clean_username}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
            {/* Puck Selector Component */}
            <PuckListed
              selectedUser={selectedUser}
              onPuckSelect={handlePuckSelect}
              selectedPuck={selectedPuck}
            />
            <Button
              sdsType="primary"
              sdsStyle="rounded"
              startIcon={<Icon sdsIcon="Plus" sdsSize="s"/>}
              onClick={handleAddPuck}
              sx={{ marginTop: '10px' }}
            >
              Add puck
            </Button>
          </CardContent>
        </Card>
        
        {/* Puck Details Component - appears on the right when a puck is selected */}
        {selectedPuck && (
          <PuckDetails 
            selectedPuck={selectedPuck}
            onAddGridBox={handleAddGridBox}
            onSlotSelect={handleSlotSelect}
            selectedSlot={selectedSlot}
          />
        )}
      </Box>

      {/* Bottom Section - Grid Box Information */}
      {selectedSlot && selectedPuck && (
        <Box className={styles.bottomSection}>
          <GridBoxInfo
            selectedPuck={selectedPuck}
            selectedSlot={selectedSlot}
            onClose={handleCloseSlotDetails}
            onAddGridBox={handleAddGridBox}
          />
        </Box>
      )}
    </Box>
  );
};