'use client';

import React, { useState, useEffect } from 'react';
import { 
  Box,  
  CircularProgress, 
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select
} from '@mui/material';
import { Button, Dialog, DialogTitle, DialogContent } from '@czi-sds/components';
import { UsersList } from '@app/common/types/gridLogging/userList';
import { useGridLoggingChoices } from '@app/common/hooks/useGridLogging/useGridLoggingChoices';
import { useGridLoggingUserList } from '@app/common/hooks/useGridLogging/useGridLoggingUserList';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';
import {useCreatePuck} from '@app/common/hooks/useGridLogging/useCreatePuck';
import { DJANGO_URL } from '@app/common/constants/api';

interface AddPuckProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UsersList | null;
  caneId?: number;
  onPuckCreated: (puck: any) => void;
}

export const AddPuck: React.FC<AddPuckProps> = ({
  open,
  onClose,
  selectedUser,
  caneId,
  onPuckCreated,

}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    user: selectedUser?.id || 0,
    puckName: '',
    color: '',
    cane: caneId || '',
    positionInCane: ''
  });

  // state for tracking filled positions
  const [filledPositions, setFilledPositions] = useState<number[]>([]);

  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { isSuccess: usersLoaded } = useGridLoggingUserList();
  const { createPuck, isCreating, error } = useCreatePuck();

  useEffect(() => {
    if (selectedUser?.id) {
      setFormData(prev => ({
        ...prev,
        user: selectedUser.id
      }));
    }
  }, [selectedUser?.id]);

 
  const fetchFilledPositions = async (caneId: number) => {
    try {
      const response = await fetch(`${DJANGO_URL}/api/list/pucks/`);
      const data = await response.json();
      
      // Filter pucks by cane 
      const filteredPucks = data.pucks?.filter((puck: any) => puck.cane === caneId) || [];
      const positions = filteredPucks.map((puck: any) => puck.position_in_cane);
      
      setFilledPositions(positions);
    } catch (error) {
      setFilledPositions([]);
    }
  };

  // fetch positions when cane changes
  useEffect(() => {
    if (formData.cane) {
      fetchFilledPositions(Number(formData.cane));
      // Reset position selection when cane changes
      setFormData(prev => ({
        ...prev,
        positionInCane: ''
      }));
    } else {
      setFilledPositions([]);
    }
  }, [formData.cane]);

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    // Validate required fields
    if (!selectedUser?.id || formData.user === 0 || !formData.puckName || !formData.color || !formData.cane || !formData.positionInCane) {
      alert('Please fill in all required fields');
      return;
    }

    const newPuck = await createPuck({
      user_id: Number(formData.user),
      puckName: formData.puckName,
      color: formData.color,
      cane: Number(formData.cane),
      position_in_cane: Number(formData.positionInCane),
    });
    if (newPuck) {
      if (onPuckCreated) {
        onPuckCreated(newPuck);
      }
      onClose();
      // Reset form
      setFormData({
        user: selectedUser?.id || 0,
        puckName: '',
        color: '',
        cane: caneId || '',
        positionInCane: ''
      });
    }
  };
 
  return (
    <Dialog 
      onClose={onClose} 
      open={open} 
      sdsSize="xs"
    >
      <DialogTitle 
        title='Add Puck' 
        subtitle= {`${selectedUser?.full_name||''}`}
        onClose={onClose} 
      />
      <DialogContent>    
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: 3,
          pt: 2,
          pb: 2,
          mt: 2,
        }}>
         
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              required
              label="Puck Name"
              placeholder="Ex. Puck 4"
              value={formData.puckName}
              onChange={(e) => handleInputChange('puckName', e.target.value)}
              sx={{ ...disabledTextFieldStyles,flex: 1 }}
            />
             <FormControl required sx={{ flex: 1 }}>
              <InputLabel id="cane-label">Cane</InputLabel>
              <Select
                labelId="cane-label"
                value={formData.cane}
                onChange={(e) => handleInputChange('cane', e.target.value)}
                label="Cane"
                sx={disabledTextFieldStyles}
              >
                <MenuItem value={1}>Cane 1</MenuItem>
                <MenuItem value={2}>Cane 2</MenuItem>
                <MenuItem value={3}>Cane 3</MenuItem>
                <MenuItem value={4}>Cane 4</MenuItem>
              </Select>
            </FormControl>
          </Box>

          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControl required sx={{ flex: 1 }}>
              <InputLabel id="color-label">Color</InputLabel>
              <Select
                labelId="color-label"
                value={formData.color}
                onChange={(e) => handleInputChange('color', e.target.value)}
                label="Color"
                disabled={!choicesLoaded}
                sx={disabledTextFieldStyles}
              >
                {choices?.puck_colors?.map((color) => (
                  <MenuItem key={color.value} value={color.value}>
                    {color.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl required sx={{ flex: 1 }}>
              <InputLabel id="position-label">Position in Cane</InputLabel>
              <Select
                labelId="position-label"
                value={formData.positionInCane}
                onChange={(e) => handleInputChange('positionInCane', e.target.value)}
                label="Position in Cane"
                sx={disabledTextFieldStyles}
              >
                {/* Show all positions with status indicators */}
                {Array.from({ length: 10 }, (_, i) => i + 1).map((position) => {
                  const isFilled = filledPositions.includes(position);
                  return (
                    <MenuItem 
                      key={position} 
                      value={position}
                      disabled={isFilled}
                    >
                      Position {position} {isFilled ? '(Filled)' : '(Available)'}
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>
          </Box>

          {/* Action Buttons */}
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'flex-end', 
            gap: 2,
          }}>
            <Button
              sdsType="secondary"
              sdsStyle="rounded"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              sdsType="primary"
              sdsStyle="rounded"
              onClick={handleSave}
              disabled={isSubmitting || !choicesLoaded || !usersLoaded}
              startIcon={isSubmitting ? <CircularProgress size={16} /> : undefined}
            >
              {isSubmitting ? 'Saving...' : 'Save'}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};