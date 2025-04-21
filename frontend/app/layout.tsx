import { AppRouterCacheProvider } from "@mui/material-nextjs/v14-appRouter";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "@app/globals.css";
import { ThemeProvider } from "@mui/material/styles";
import { theme } from "@app/common/theme";
import { TopNavigation } from "./components/TopNavigation/TopNavigation";
import { cookies } from "next/headers";
import { FeatureFlagsProvider } from "./common/context/FeatureFlagsProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Embrella",
};

const CACHE_PROVIDER_OPTIONS = {
  key: "css",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const featureFlagsCookie = await cookies().get("feature_flags")?.value;

  return (
    <html lang="en">
      <body className={inter.className}>
        <AppRouterCacheProvider options={CACHE_PROVIDER_OPTIONS}>
          <ThemeProvider theme={theme}>
            <FeatureFlagsProvider featureFlagsCookie={featureFlagsCookie}>
              <TopNavigation />
              {children}
            </FeatureFlagsProvider>
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
