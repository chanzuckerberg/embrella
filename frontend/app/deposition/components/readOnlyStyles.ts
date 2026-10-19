// A tinted field with a dashed border marks a stored value that can be selected and copied.
export const READ_ONLY_FIELDS_SX = {
  '& .MuiInputBase-root.Mui-readOnly, & .MuiInputBase-root:has(input[readonly], textarea[readonly])': {
    bgcolor: 'action.hover',
    '& .MuiOutlinedInput-notchedOutline': { borderStyle: 'dashed' },
  },
  '& .MuiInputBase-input[readonly]': { cursor: 'text' },
};
