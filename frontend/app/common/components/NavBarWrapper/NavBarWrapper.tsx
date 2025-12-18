'use client';

import { usePathname } from 'next/navigation';
import { TopNavigation } from '@app/components/TopNavigation/TopNavigation';

export function NavbarWrapper() {
  const pathname = usePathname();
  const hideNavbar = /^\/processing\/tomograms\/reviews\/[^/]+$/.test(pathname); // match viewer route

  if (hideNavbar) return null;
  return <TopNavigation />;
}
