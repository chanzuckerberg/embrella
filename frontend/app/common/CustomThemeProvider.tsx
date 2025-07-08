'use client';

import { SDSLightAppTheme, SDSDarkAppTheme, makeThemeOptions } from '@czi-sds/components';
import { createTheme, CssBaseline } from '@mui/material';
import { Theme, ThemeProvider } from '@mui/material/styles';
import { ReactNode } from 'react';
import { customThemeLight, customThemeDark } from './theme';
import { deepmerge } from '@mui/utils';

export type ThemeMode = 'light' | 'dark';

const updateTheme = (themeMode: ThemeMode): Theme => {
  const baseTheme = themeMode === 'light' ? SDSLightAppTheme : SDSDarkAppTheme;
  const customTheme = themeMode === 'light' ? customThemeLight : customThemeDark;

  const themeOptions = deepmerge(baseTheme, customTheme);

  const appTheme = makeThemeOptions(themeOptions, themeMode);
  return createTheme(appTheme, {
    cssVariables: true,
  });
};

// CustomThemeProvider component to wrap your app
export const CustomThemeProvider = ({ children }: { children: ReactNode }) => {
  const theme = updateTheme('light');

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
};
