'use client';

import { usePathname } from 'next/navigation';

interface ContentWrapperProps {
  children: React.ReactNode;
}

export function ContentWrapper({ children }: ContentWrapperProps) {
  const pathname = usePathname();
  const isDepositionWizard = /^\/deposition\/wizard\/[^/]+$/.test(pathname);
  // Full-width pages without a navbar (e.g., tomogram viewer).
  const isFullWidthPage = /^\/processing\/tomograms\/reviews\/[^/]+$/.test(pathname);

  if (isFullWidthPage) {
    return <>{children}</>;
  }

  // Metadata viewer page with smaller navbar offset
  const isMetadataViewerPage = /^\/metadata\/view\/[^/]+\/[^/]+$/.test(pathname);

  if (isMetadataViewerPage) {
    return (
      <div
        style={{
          paddingTop: '65px',
        }}
      >
        {children}
      </div>
    );
  }

  return (
    <div
      style={{
        maxWidth: '95rem',
        marginLeft: 'auto',
        marginRight: 'auto',
        ...(isDepositionWizard && { '--wizard-top-offset': 'clamp(72px, 10dvh, 110px)' }),
        paddingTop: isDepositionWizard ? 'var(--wizard-top-offset)' : '130px',
      }}
    >
      {children}
    </div>
  );
}
