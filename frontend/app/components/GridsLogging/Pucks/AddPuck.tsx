'use client';

import React, { useState } from 'react';
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
import { DJANGO_URL } from '@app/common/constants/api';
import { disabledTextFieldStyles } from '../GridBox/DisableBoxStyle';

interface AddPuckProps {
  open: boolean;
  onClose: () => void;
  selectedUser?: UsersList | null;
  caneId?: number;
}

export const AddPuck: React.FC<AddPuckProps> = ({
  open,
  onClose,
  selectedUser,
  caneId
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    user: selectedUser?.id || '',
    puckName: '',
    color: '',
    cane: caneId || '',
    positionInCane: ''
  });

  const { choices, isSuccess: choicesLoaded } = useGridLoggingChoices();
  const { isSuccess: usersLoaded } = useGridLoggingUserList();

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = () => {
    // Validate required fields
    if (!formData.user || !formData.puckName || !formData.color || !formData.cane || !formData.positionInCane) {
      alert('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    
    // Build URL with prefill parameters
    const prefillParams = new URLSearchParams();
    prefillParams.append('user', formData.user.toString());
    prefillParams.append('name', formData.puckName);
    prefillParams.append('color', formData.color);
    prefillParams.append('cane', formData.cane.toString());
    prefillParams.append('position_in_cane', formData.positionInCane.toString());

    // Add return state parameters
    if (selectedUser?.id) {
      prefillParams.append('return_user_id', selectedUser.id.toString());
    }

    const adminUrl = `${DJANGO_URL}/admin/cryo_grids/cryopuck/add/?${prefillParams.toString()}`;
    window.location.href = adminUrl;
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
          // maxHeight:'200px'
        }}>
         
          <Box sx={{ display: 'flex', gap: 2 }}>
            {/* <TextField
              label="User"
              value={selectedUser?.full_name || ''}
              disabled
              sx={{ ...disabledTextFieldStyles, flex: 1 }}
            /> */}
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
                {Array.from({ length: 10 }, (_, i) => i + 1).map((position) => (
                  <MenuItem key={position} value={position}>
                    Position {position}
                  </MenuItem>
                ))}
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