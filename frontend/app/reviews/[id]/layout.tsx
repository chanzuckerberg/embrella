import { AppRouterCacheProvider } from "@mui/material-nextjs/v14-appRouter";
import { ThemeProvider } from "@mui/material/styles";
import { theme } from "@app/common/theme";
import { FeatureFlagsProvider } from "@app/common/context/FeatureFlagsProvider";
import { cookies } from "next/headers";
import { COOKIE_NAME } from "@app/common/types/cookies";
import { Inter } from "next/font/google";
import "@app/globals.css";

const inter = Inter({ subsets: ["latin"] });

const CACHE_PROVIDER_OPTIONS = {
    key: "css",
};

export default function ReviewLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const featureFlagsCookie = cookies().get(COOKIE_NAME.FEATURE_FLAGS)?.value;

    return (
        <html lang="en">
            <body className={inter.className}>
                <AppRouterCacheProvider options={CACHE_PROVIDER_OPTIONS}>
                    <ThemeProvider theme={theme}>
                        <FeatureFlagsProvider featureFlagsCookie={featureFlagsCookie}>
                            {children}
                        </FeatureFlagsProvider>
                    </ThemeProvider>
                </AppRouterCacheProvider>
            </body>
        </html>
    );
}