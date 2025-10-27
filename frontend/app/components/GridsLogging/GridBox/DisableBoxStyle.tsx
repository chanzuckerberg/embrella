// import { SxProps, Theme } from '@mui/material';

// export const disabledTextFieldStyles: SxProps<Theme> = {
//   mb: 5,
//   '& .MuiInputBase-input.Mui-disabled': {
//     color: 'black',
//     WebkitTextFillColor: 'black',
//   },
//   '& .MuiInputLabel-root.Mui-disabled': {
//     color: 'rgba(0, 0, 0, 0.6)',
//   },
// };

import { SxProps, Theme } from '@mui/material';

export const disabledTextFieldStyles: SxProps<Theme> = {
  mb: 5,
  '& .MuiInputBase-root.Mui-disabled': {
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
  },
  '& .MuiInputBase-input.Mui-disabled': {
    color: 'rgba(0, 0, 0, 0.7)',
    WebkitTextFillColor: 'rgba(0, 0, 0, 0.7)',
  },
  '& .MuiInputLabel-root.Mui-disabled': {
    color: 'rgba(0, 0, 0, 0.6)',
  },
};
