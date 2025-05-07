import { AppRouterCacheProvider } from '@mui/material-nextjs/v14-appRouter';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@app/globals.css';
import { ThemeProvider } from '@mui/material/styles';
import { theme } from '@app/common/theme';
import { NavbarWrapper } from '@app/common/components/NavBarWrapper';
import { cookies } from 'next/headers';
import { FeatureFlagsProvider } from './common/context/FeatureFlagsProvider';
import { COOKIE_NAME } from './common/types/cookies';
import { UserProvider } from './common/context/UserProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Embrella',
};

const CACHE_PROVIDER_OPTIONS = {
  key: 'css',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const featureFlagsCookie = cookies().get(COOKIE_NAME.FEATURE_FLAGS)?.value;

  return (
    <html lang="en">
      <body className={inter.className}>
        <AppRouterCacheProvider options={CACHE_PROVIDER_OPTIONS}>
          <ThemeProvider theme={theme}>
            <UserProvider>
              <FeatureFlagsProvider featureFlagsCookie={featureFlagsCookie}>
                <NavbarWrapper />
                {children}
              </FeatureFlagsProvider>
            </UserProvider>
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
