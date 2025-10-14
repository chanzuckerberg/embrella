'use client';

import React, { useState, useEffect, useContext, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import { useGridLoggingPucksByUser } from '@app/common/hooks/useGridLogging/useGridLoggingPuckList';
import { UserContext } from '@app/common/context/UserProvider';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { PucksList } from '@app/common/types/gridLogging/puckList';
import styles from './GridLogging.module.css';
import { PuckListed } from './Pucks/PuckListed';
import { PuckDetails } from './Pucks/PuckDetails';
import { GridBoxInfo } from './GridBox/GridBoxInfo';
import { GridDetails } from './Grid/GridDetails';
import { Card, CardContent, CardHeader, Box, Typography, Autocomplete, TextField } from '@mui/material';
import { Button, Icon } from '@czi-sds/components';
import { AddPuck } from './Pucks/AddPuck';

export const GridsLogging: React.FC = () => {
  const [selectedUser, setSelectedUser] = useState<UsersList | null>(null);
  const [selectedPuck, setSelectedPuck] = useState<PucksList | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [selectedGrid, setSelectedGrid] = useState<number | null>(null);
  const [selectedGridId, setSelectedGridId] = useState<number | null>(null);
  const [isAddPuckDialogOpen, setIsAddPuckDialogOpen] = useState(false);
  const { users } = useGridLoggingUserList();
  const currentUser = useContext(UserContext);
  const searchParams = useSearchParams();

  // Fetch pucks for the selected user
  const { pucks: pucksData } = useGridLoggingPucksByUser(selectedUser?.id);

  // Extract users array from the response object
  const usersList = useMemo(() => users?.users || [], [users]);

  // Extract pucks array from the response object
  const pucksList = useMemo(() => pucksData?.pucks || [], [pucksData]);

  // Restore state from URL parameters
  useEffect(() => {
    const userId = searchParams.get('user_id');
    const puckId = searchParams.get('puck_id');
    const slotPosition = searchParams.get('slot_position');
    const gridPosition = searchParams.get('grid_position');
    const gridId = searchParams.get('grid_id');

    // Restore user selection
    if (userId && usersList.length > 0) {
      const user = usersList.find((u) => String(u.id) === userId);
      if (user) {
        setSelectedUser(user);
      }
    }

    // Restore puck selection - now that we have pucksList
    if (puckId && pucksList.length > 0) {
      const puck = pucksList.find((p) => String(p.id) === puckId);
      if (puck) {
        setSelectedPuck(puck);
      }
    }
    // Restore slot selection
    if (slotPosition) {
      setSelectedSlot(parseInt(slotPosition));
    }

    // Restore grid selection
    if (gridPosition) {
      setSelectedGrid(parseInt(gridPosition));
    }

    if (gridId) {
      setSelectedGridId(parseInt(gridId));
    }
  }, [searchParams, usersList, pucksList]);

  // Set the current user as default when users are loaded (only if no URL params)
  useEffect(() => {
    if (usersList.length > 0 && currentUser && !selectedUser && !searchParams.get('user_id')) {
      // Find the current user in the users list
      const foundUser = usersList.find((u) => String(u.id) === String(currentUser.id));
      if (foundUser) {
        setSelectedUser(foundUser);
      }
    }
  }, [usersList, currentUser, selectedUser, searchParams]);

  // Handle user selection - updated for Autocomplete
  const handleUserChange = (event: React.SyntheticEvent, newValue: UsersList | null) => {
    setSelectedUser(newValue);
    // Reset selected puck and slot when user changes
    setSelectedPuck(null);
    setSelectedSlot(null);
  };

  const handleAddPuck = () => {
    setIsAddPuckDialogOpen(true)
  };

  const handlePuckSelect = (puck: PucksList | null) => {
    setSelectedPuck(puck);
    // Reset selected slot when puck changes
    setSelectedSlot(null);
  };

  const handleSlotSelect = (slotPosition: number, _gridBoxId?: number) => {
    setSelectedSlot(slotPosition);
    // Reset grid selection when slot changes
    setSelectedGrid(null);
    setSelectedGridId(null);
  };

  const handleGridSelect = (gridPosition: number, gridId?: number) => {
    setSelectedGrid(gridPosition);
    setSelectedGridId(gridId || null);
  };

  return (
    <Box className={styles.mainContainer}>
      {/* Top Section - Puck List and Puck Details */}
      <Box className={styles.topSection}>
        <Card elevation={2} className={styles.leftCard}>
          <CardHeader
            title={
              <Box className={styles.cardHeader}>
                <Typography variant="h6" component="h2">
                  Pucks
                </Typography>
                <Button
                  sdsType="primary"
                  sdsStyle="rounded"
                  startIcon={<Icon sdsIcon="Plus" sdsSize="s" />}
                  onClick={handleAddPuck}
                  size="small"
                >
                  Add puck
                </Button>
              </Box>
            }
          />
          <CardContent>
            <Box className={styles.userSelectionContainer}>
              <Autocomplete
                value={selectedUser}
                onChange={handleUserChange}
                options={usersList}
                getOptionLabel={(option) => option.username || ''}
                isOptionEqualToValue={(option, value) => option.id === value?.id}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select User"
                    variant="outlined"
                    size="small"
                    className={styles.userDropdown}
                  />
                )}
                noOptionsText="No users found"
                ListboxProps={{
                  sx: {
                    maxHeight: 150, // 👈 reduce dropdown height
                  },
                }}
              />
            </Box>
            {/* Puck Selector Component */}
            <PuckListed selectedUser={selectedUser} onPuckSelect={handlePuckSelect} selectedPuck={selectedPuck} />
          </CardContent>
        </Card>

        {/* Puck Details Component - appears on the right when a puck is selected */}
        {selectedPuck && (
          <PuckDetails selectedPuck={selectedPuck} onSlotSelect={handleSlotSelect} selectedUser={selectedUser} />
        )}
      </Box>

      {!!selectedSlot && selectedPuck && (
        <Box className={styles.bottomSection}>
          <GridBoxInfo
            selectedPuck={selectedPuck}
            selectedSlot={selectedSlot}
            onGridSelect={handleGridSelect}
            selectedUser={selectedUser}
          />
          {!!selectedGrid && (
            <GridDetails
              selectedPuck={selectedPuck}
              selectedSlot={selectedSlot}
              selectedGrid={selectedGrid}
              selectedGridId={selectedGridId}
              selectedUser={selectedUser}
            />
          )}
        </Box>
      )}
    <AddPuck 
      open={isAddPuckDialogOpen} 
      onClose={() => setIsAddPuckDialogOpen(false)} 
      selectedUser={selectedUser} 
      caneId={1} 
    />
 
    </Box>
  );
};
