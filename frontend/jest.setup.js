// Add custom jest matchers from jest-dom
import '@testing-library/jest-dom';

// Avoid loading full MUI barrels; see testing/muiImportOptimizer.js
// Factories run hoisted, so `require`, not `import`
/* global jest */
/* eslint-disable @typescript-eslint/no-require-imports */
jest.mock('@mui/material', () => require('./testing/muiImportOptimizer').material);
jest.mock('@mui/icons-material', () => require('./testing/muiImportOptimizer').iconsMaterial);
