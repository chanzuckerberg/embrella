import { AppRouterCacheProvider } from '@mui/material-nextjs/v14-appRouter';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import '@app/globals.css';
import { NavbarWrapper } from '@app/common/components/NavBarWrapper';
import { CustomThemeProvider } from './common/CustomThemeProvider';
import { UserProvider } from './common/context/UserProvider';
import { IdetikProvider } from '../imaging-active-learning/packages/react/src/components/providers/IdetikProvider';
import { FeatureFlagsProvider } from './common/context/FeatureFlagsProvider';
import { cookies } from 'next/headers';
import { COOKIE_NAME } from './common/types/cookies';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Embrella',
};

const CACHE_PROVIDER_OPTIONS = {
  key: 'sds',
  prepend: true,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const featureFlagsCookie = cookies().get(COOKIE_NAME.FEATURE_FLAGS)?.value;

  return (
    <html lang="en">
      <body className={inter.className}>
        <IdetikProvider>
          <AppRouterCacheProvider options={CACHE_PROVIDER_OPTIONS}>
            <CustomThemeProvider>
              <UserProvider>
                <FeatureFlagsProvider featureFlagsCookie={featureFlagsCookie}>
                  <NavbarWrapper />
                  {children}
                </FeatureFlagsProvider>
              </UserProvider>
            </CustomThemeProvider>
          </AppRouterCacheProvider>
        </IdetikProvider>
      </body>
    </html>
  );
}
