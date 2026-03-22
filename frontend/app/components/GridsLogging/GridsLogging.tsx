'use client';

import React, { useState, useEffect, useContext, useMemo, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  Box,
  Typography,
  Autocomplete,
  TextField,
  InputAdornment,
  IconButton,
} from '@mui/material';
import { parseAsInteger, parseAsString, useQueryStates } from 'nuqs';
import { Button, Icon } from '@czi-sds/components';
import {
  useGridLoggingUserList,
  useGridLoggingPucksList,
  useGridLoggingPucksByUser,
} from '@app/common/hooks/useGridLogging';
import { UserList, PuckList } from '@app/common/types/gridLogging';
import { UserContext } from '@app/common/context/UserProvider';
import styles from './GridLogging.module.css';
import { PuckListed } from './Pucks/PuckListed';
import { PuckDetails } from './Pucks/PuckDetails';
import { GridBoxInfo } from './GridBox/GridBoxInfo';
import { GridDetails } from './Grid/GridDetails';
import { AddPuck } from './Pucks/AddPuck';

const gridLoggingParsers = {
  user_id: parseAsInteger,
  puck_id: parseAsInteger,
  slot_position: parseAsInteger,
  grid_position: parseAsInteger,
  grid_id: parseAsInteger,
  puck_search: parseAsString,
};

const NUQS_OPTIONS = { history: 'replace' as const, shallow: true, clearOnDefault: true };

export const GridsLogging: React.FC = () => {
  const [urlState, setUrlState] = useQueryStates(gridLoggingParsers, NUQS_OPTIONS);
  const [isAddPuckDialogOpen, setIsAddPuckDialogOpen] = useState(false);
  const [puckDetailsRefetch, setPuckDetailsRefetch] = useState<() => void>(() => {});
  const [gridDetailsRefetch, setGridDetailsRefetch] = useState<() => void>(() => {});
  const [gridBoxInfoRefetch, setGridBoxInfoRefetch] = useState<() => void>(() => {});

  const { users } = useGridLoggingUserList();
  const currentUser = useContext(UserContext);

  // Fetch pucks for the selected user — uses URL state directly for immediate deep-link support
  const { pucks: pucksData, refetch: refetchPuckList } = useGridLoggingPucksByUser(urlState.user_id ?? undefined);

  // Also fetch ALL pucks for search purposes
  const { pucks: allPucksData } = useGridLoggingPucksList();

  // Extract users array from the response object
  const usersList = useMemo(() => users?.users || [], [users]);

  // Extract pucks array from the response object
  const pucksList = useMemo(() => pucksData?.pucks || [], [pucksData]);
  const allPucksList = useMemo(() => allPucksData?.pucks || [], [allPucksData]);

  // Derive objects from URL IDs
  const selectedUser = useMemo(
    () => usersList.find((u) => u.id === urlState.user_id) ?? null,
    [usersList, urlState.user_id]
  );
  const selectedPuck = useMemo(
    () => pucksList.find((p) => p.id === urlState.puck_id) ?? null,
    [pucksList, urlState.puck_id]
  );
  const selectedSlot = urlState.slot_position;
  const selectedGrid = urlState.grid_position;
  const selectedGridId = urlState.grid_id;
  const puckSearchQuery = urlState.puck_search ?? '';

  // Filter pucks based on search query
  const filteredPucksList = useMemo(() => {
    if (!puckSearchQuery.trim()) {
      return pucksList;
    }
    return allPucksList.filter((puck) => `CZII-0${puck.name}`.toLowerCase().includes(puckSearchQuery.toLowerCase()));
  }, [pucksList, allPucksList, puckSearchQuery]);

  // Set the current user as default when users are loaded (only if no URL user_id)
  useEffect(() => {
    if (usersList.length > 0 && currentUser && !urlState.user_id) {
      const foundUser = usersList.find((u) => String(u.id) === String(currentUser.id));
      if (foundUser) {
        setUrlState({ user_id: foundUser.id });
      }
    }
  }, [usersList, currentUser, urlState.user_id, setUrlState]);

  // Handle user selection - updated for Autocomplete
  const handleUserChange = (event: React.SyntheticEvent, newValue: UserList | null) => {
    setUrlState({
      user_id: newValue?.id ?? null,
      puck_id: null,
      slot_position: null,
      grid_position: null,
      grid_id: null,
      puck_search: null,
    });
  };

  const handleAddPuck = () => {
    setIsAddPuckDialogOpen(true);
  };

  const handlePuckSelect = (puck: PuckList | null) => {
    setUrlState({
      puck_id: puck?.id ?? null,
      slot_position: null,
      grid_position: null,
      grid_id: null,
    });
  };
  const handleGridDetailsRefetchReady = useCallback((refetch: () => void) => {
    setGridDetailsRefetch(() => refetch);
  }, []);

  const handleSlotSelect = (slotPosition: number, _gridBoxId?: number) => {
    setUrlState({
      slot_position: slotPosition,
      grid_position: null,
      grid_id: null,
    });
  };

  const handleGridSelect = (gridPosition: number, gridId?: number) => {
    setUrlState({
      grid_position: gridPosition,
      grid_id: gridId ?? null,
    });
  };
  const handlePuckCreated = (_newPuck: PuckList) => {
    window.location.reload();
  };
  const handlePuckDeleted = () => {
    if (refetchPuckList) {
      refetchPuckList();
    }
    setUrlState({
      puck_id: null,
      slot_position: null,
      grid_position: null,
      grid_id: null,
    });
  };

  const handleMoveGridBoxSuccess = (newPuckId: number, newSlotPosition: number) => {
    setUrlState({
      puck_id: newPuckId,
      slot_position: newSlotPosition,
      grid_position: null,
      grid_id: null,
    });
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
    setUrlState({
      puck_id: newPuckId,
      slot_position: newSlotPosition,
      grid_position: newPositionInBox,
    });

    // Refetch all related data to show updated locations
    if (puckDetailsRefetch) {
      puckDetailsRefetch();
    }
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

            {/* Search box for pucks */}
            {selectedUser && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 4, mt: -6 }}>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Search pucks by name..."
                  value={puckSearchQuery}
                  onChange={(e) => setUrlState({ puck_search: e.target.value || null })}
                  variant="outlined"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <Icon sdsIcon="Search" sdsSize="l" />
                      </InputAdornment>
                    ),
                    endAdornment: puckSearchQuery && (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => setUrlState({ puck_search: null })} edge="end">
                          <Icon sdsIcon="XMark" sdsSize="l" />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </Box>
            )}

            {/* Puck Selector Component */}
            <PuckListed
              selectedUser={selectedUser}
              onPuckSelect={handlePuckSelect}
              selectedPuck={selectedPuck}
              puckList={filteredPucksList}
            />
          </CardContent>
        </Card>

        {/* Puck Details Component - appears on the right when a puck is selected */}
        {selectedPuck && (
          <PuckDetails
            selectedPuck={selectedPuck}
            onSlotSelect={handleSlotSelect}
            selectedUser={selectedUser}
            onRefetchReady={handlePuckDetailsRefetchReady}
            onGridBoxInfoRefetchReady={handleGridBoxInfoRefetchReady}
            onPuckDeleted={handlePuckDeleted}
          />
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
            onGridBoxDeleted={() => {
              setUrlState({ slot_position: null, grid_position: null, grid_id: null });
              if (puckDetailsRefetch) {
                puckDetailsRefetch();
              }
            }}
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
