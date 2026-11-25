'use client';

import { SDSLightAppTheme, SDSDarkAppTheme, makeThemeOptions } from '@czi-sds/components';
import { createTheme, CssBaseline } from '@mui/material';
import { Theme, ThemeProvider } from '@mui/material/styles';
import { ReactNode } from 'react';
import { customThemeLight, customThemeDark } from './theme';
import { deepmerge } from '@mui/utils';

export type ThemeMode = 'light' | 'dark';

const POPUP_TRANSITION_MS = 100;

const updateTheme = (themeMode: ThemeMode): Theme => {
  const baseTheme = themeMode === 'light' ? SDSLightAppTheme : SDSDarkAppTheme;
  const customTheme = themeMode === 'light' ? customThemeLight : customThemeDark;

  const themeOptions = deepmerge(baseTheme, customTheme);

  const appTheme = makeThemeOptions(themeOptions, themeMode);

  // Convert the array-based spacing to a function so MUI internal components
  // can use fractional values like spacing(0.5) without errors.
  // Integer indices still map to the SDS spacing array values.
  const sdsSpacingArray = appTheme.spacing as number[];
  const spacingFn = (factor: number) => {
    if (Number.isInteger(factor) && factor >= 0 && factor < sdsSpacingArray.length) {
      return sdsSpacingArray[factor];
    }
    return factor * 8;
  };

  // MUI's 'auto' open animation lengthens with menu height (long menus feel sluggish); cap it.
  // Menu passes its own duration to Popover, so both need it; Select opens a Menu.
  const components = deepmerge(appTheme.components ?? {}, {
    MuiMenu: { defaultProps: { transitionDuration: POPUP_TRANSITION_MS } },
    MuiPopover: { defaultProps: { transitionDuration: POPUP_TRANSITION_MS } },
  });

  return createTheme(
    { ...appTheme, spacing: spacingFn, components },
    {
      cssVariables: true,
    }
  );
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
