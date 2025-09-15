'use client';

import React, { useState, useEffect, useContext } from 'react';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import {  UserContext } from '@app/common/context/UserProvider';
import {  UsersList } from '@app/common/types/gridLogging/userList';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import styles from './GridLogging.module.css';
import { PuckListed } from './PuckListed';
import { PuckDetails } from './PuckDetails';
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


interface GridsLoggingProps {
  onAddPuck?: () => void;
}

export const GridsLogging: React.FC<GridsLoggingProps> = ({
  onAddPuck,
}) => {

  const [selectedUser, setSelectedUser] = useState<UsersList | null>(null);
  const [selectedPuck, setSelectedPuck] = useState<PucksList | null>(null);
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
      // Reset selected puck when user changes
      setSelectedPuck(null);
  };

  const handlePuckSelect = (puck: PucksList | null) => {
    setSelectedPuck(puck);
  };
  return (
    <Box className={`${styles.cardContainer} ${selectedPuck ? styles.withPuckSelected : ''}`}>
      <Card elevation={2} className={styles.leftCard}>
        <CardHeader title="Pucks" />
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 7, flexGrow: 1 }}>
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
           onClick={onAddPuck}
           sx={{ marginTop: '10px' }}
           >
             Add puck
           </Button>
        </CardContent>
      </Card>
      
      {/* Puck Details Component - appears on the right when a puck is selected */}
      <PuckDetails 
        selectedPuck={selectedPuck}
      />
    </Box>
  );
};