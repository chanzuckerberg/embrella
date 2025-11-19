'use client';

import React, { useState, useEffect, useContext, useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, Box, Typography, Autocomplete, TextField } from '@mui/material';
import { useSearchParams } from 'next/navigation';
import { Button, Icon } from '@czi-sds/components';
import { useGridLoggingUserList, useGridLoggingPucksByUser } from '@app/common/hooks/useGridLogging';
import { UserList, PuckList } from '@app/common/types/gridLogging';
import { UserContext } from '@app/common/context/UserProvider';
import styles from './GridLogging.module.css';
import { PuckListed } from './Pucks/PuckListed';
import { PuckDetails } from './Pucks/PuckDetails';
import { GridBoxInfo } from './GridBox/GridBoxInfo';
import { GridDetails } from './Grid/GridDetails';
import { AddPuck } from './Pucks/AddPuck';

export const GridsLogging: React.FC = () => {
  const [selectedUser, setSelectedUser] = useState<UserList | null>(null);
  const [selectedPuck, setSelectedPuck] = useState<PuckList | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [selectedGrid, setSelectedGrid] = useState<number | null>(null);
  const [selectedGridId, setSelectedGridId] = useState<number | null>(null);
  const [isAddPuckDialogOpen, setIsAddPuckDialogOpen] = useState(false);
  const [puckDetailsRefetch, setPuckDetailsRefetch] = useState<() => void>(() => {});
  const [gridDetailsRefetch, setGridDetailsRefetch] = useState<() => void>(() => {});
  const [gridBoxInfoRefetch, setGridBoxInfoRefetch] = useState<() => void>(() => {});

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
  const handleUserChange = (event: React.SyntheticEvent, newValue: UserList | null) => {
    setSelectedUser(newValue);
    // Reset selected puck and slot when user changes
    setSelectedPuck(null);
    setSelectedSlot(null);
  };

  const handleAddPuck = () => {
    setIsAddPuckDialogOpen(true);
  };

  const handlePuckSelect = (puck: PuckList | null) => {
    setSelectedPuck(puck);
    // Reset selected slot when puck changes
    setSelectedSlot(null);
  };
  const handleGridDetailsRefetchReady = useCallback((refetch: () => void) => {
    setGridDetailsRefetch(() => refetch);
  }, []);

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
  const handlePuckCreated = (_newPuck: PuckList) => {
    window.location.reload();
  };

  const handleMoveGridBoxSuccess = (newPuckId: number, newSlotPosition: number) => {
    const newPuck = pucksList?.find(p => p.id === newPuckId);
    if (newPuck) {
      setSelectedPuck(newPuck);
      setSelectedSlot(newSlotPosition);
      setSelectedGrid(null);
      setSelectedGridId(null);
    }
    if (puckDetailsRefetch) {
      puckDetailsRefetch();
    }
  };
  const handleMoveGridSuccess = (
    newPuckId: number, 
    newSlotPosition: number, 
    newGridBoxId: number, 
    newPositionInBox: number
  ) => {
    // Find and set the new puck
    const newPuck = pucksList?.find(p => p.id === newPuckId);
    if (newPuck) {
      setSelectedPuck(newPuck);
      setSelectedSlot(newSlotPosition);
      setSelectedGrid(newPositionInBox);
      // Keep the same gridId since the grid itself hasn't changed, just moved
    }
    
    // Refetch all related data to show updated locations
    if (puckDetailsRefetch) {
      puckDetailsRefetch();
    }
    // if (gridDetailsRefetch) {
    //   gridDetailsRefetch();
    // }
    if (gridBoxInfoRefetch) {  
      gridBoxInfoRefetch();
    }
  };
  const handlePuckDetailsRefetchReady = useCallback((refetch: () => void) => {
    setPuckDetailsRefetch(() => refetch);
  }, []);

  const handleGridBoxInfoRefetchReady = useCallback((refetch: () => void) => {  
    setGridBoxInfoRefetch(() => refetch);
  }, []);

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
          <PuckDetails selectedPuck={selectedPuck} onSlotSelect={handleSlotSelect} selectedUser={selectedUser} onRefetchReady={handlePuckDetailsRefetchReady} onGridBoxInfoRefetchReady={handleGridBoxInfoRefetchReady} />
        )}
      </Box>

      {!!selectedSlot && selectedPuck && (
        <Box className={styles.bottomSection}>
          <GridBoxInfo
            selectedPuck={selectedPuck}
            selectedSlot={selectedSlot}
            onGridSelect={handleGridSelect}
            selectedUser={selectedUser}
            onGridDetailsRefetch={gridDetailsRefetch}
            onMoveGridBoxSuccess={handleMoveGridBoxSuccess}
            onGridBoxInfoRefetchReady={handleGridBoxInfoRefetchReady}
          />
          {!!selectedGrid && (
            <GridDetails
              selectedPuck={selectedPuck}
              selectedSlot={selectedSlot}
              selectedGrid={selectedGrid}
              selectedGridId={selectedGridId}
              selectedUser={selectedUser}
              onGridDetailsRefetchReady={handleGridDetailsRefetchReady}
              onMoveGridSuccess={handleMoveGridSuccess}
            />
          )}
        </Box>
      )}
      <AddPuck
        open={isAddPuckDialogOpen}
        onClose={() => setIsAddPuckDialogOpen(false)}
        selectedUser={selectedUser}
        caneId={1}
        onPuckCreated={handlePuckCreated}
      />
    </Box>
  );
};
