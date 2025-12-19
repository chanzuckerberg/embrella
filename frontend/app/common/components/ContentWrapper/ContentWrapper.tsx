'use client';

import { usePathname } from 'next/navigation';

interface ContentWrapperProps {
  children: React.ReactNode;
}

export function ContentWrapper({ children }: ContentWrapperProps) {
  const pathname = usePathname();
  // Full-width pages without navbar offset (e.g., tomogram viewer, metadata view)
  const isFullWidthPage =
    /^\/processing\/tomograms\/reviews\/[^/]+$/.test(pathname) || /^\/metadata\/view\/[^/]+\/[^/]+$/.test(pathname);

  if (isFullWidthPage) {
    return <>{children}</>;
  }

  return (
    <div
      style={{
        maxWidth: '95rem',
        marginLeft: 'auto',
        marginRight: 'auto',
        paddingTop: '130px',
      }}
    >
      {children}
    </div>
  );
}
