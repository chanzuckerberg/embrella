import { SxProps, Theme } from '@mui/material';

export const disabledTextFieldStyles: SxProps<Theme> = {
  mb: 5,
  '& .MuiInputBase-input.Mui-disabled': {
    color: 'black',
    WebkitTextFillColor: 'black',
  },
  '& .MuiInputLabel-root.Mui-disabled': {
    color: 'rgba(0, 0, 0, 0.6)',
  },
};