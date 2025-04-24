'use client';

import { usePathname } from "next/navigation";
import { TopNavigation } from "@app/components/TopNavigation/TopNavigation";

export function NavbarWrapper() {
    const pathname = usePathname();
    const hideNavbar = /^\/reviews\/[^/]+$/.test(pathname); // match viewer route

    if (hideNavbar) return null;
    return <TopNavigation />;
}
