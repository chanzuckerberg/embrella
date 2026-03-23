'use client';

import { useContext, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import styled from '@emotion/styled';
import { Link, Button, DropdownMenu, Icon } from '@czi-sds/components';
import { Box, Typography } from '@mui/material';

import { FEATURE_FLAG, FeatureFlagsContext } from '@app/common/context/FeatureFlagsProvider';
import { UserContext } from '@app/common/context/UserProvider';
import { DJANGO_URL } from '@app/common/constants/api';

// Main navigation structure
type NavSection = 'home' | 'samples' | 'sessions' | 'processing';

interface NavItem {
  label: string;
  href: string;
  section: NavSection;
}

interface SubNavItem {
  label: string;
  href: string;
}

const MAIN_NAV_ITEMS: NavItem[] = [
  { label: 'Samples', href: '/samples/grids', section: 'samples' },
  { label: 'Sessions', href: '/sessions/browse', section: 'sessions' },
  { label: 'Processing', href: '/processing/jobs/monitor', section: 'processing' },
];

// Processing section uses dropdowns instead of flat sub-nav items
// Jobs dropdown items
const JOBS_DROPDOWN_ITEMS = [
  { name: 'launch', label: 'Launch new job', href: '/processing/jobs/launch' },
  { name: 'current', label: 'View running jobs', href: '/processing/jobs/monitor' },
  { name: 'logs', label: 'View past jobs', href: '/processing/jobs/logs' },
];

// Tomograms dropdown items (Reviews is conditional on feature flag)
const getTomogramsDropdownItems = (isReviewEnabled: boolean) => {
  const items = [];
  if (isReviewEnabled) {
    items.push({ name: 'reviews', label: 'Reviews', href: '/processing/tomograms/reviews' });
  }
  items.push(
    { name: 'metadata', label: 'Metadata', href: '/processing/tomograms/metadata' },
    { name: 'annotations', label: 'Annotations', href: '/processing/tomograms/annotations' }
  );
  return items;
};

// Data dropdown items
const DATA_DROPDOWN_ITEMS = [
  { name: 'storage', label: 'Storage Explorer', href: '/processing/data/storage' },
  { name: 'export', label: 'Export', href: '/processing/data/export' },
];

const SUB_NAV_ITEMS: Record<NavSection, SubNavItem[]> = {
  home: [],
  samples: [
    { label: 'Grid Logging', href: '/samples/grid_logging' },
    { label: 'Grid Inventory', href: '/samples/cryo_grids' },
    { label: 'Grid Boxes', href: '/samples/boxes' },
    { label: 'Clear Cassette', href: '/samples/clear-cassette' },
  ],
  sessions: [
    { label: 'New TEM Session', href: '/sessions/new/tem' },
    { label: 'Screen Multiple Grids', href: '/sessions/screen' },
    { label: 'Browse Sessions', href: '/sessions/browse' },
  ],
  processing: [], // Will be populated dynamically
};

const StyledNav = styled.nav`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  width: 100%;
`;

const StyledNavbar = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 5px 8px;
  width: 100%;
  background: #000000;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
`;

const NavbarInner = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 75rem;
  margin-left: auto;
  margin-right: auto;
`;

const StyledSubNavbar = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 8px;
  width: 100%;
  background: #f5f7fa;
  border-bottom: 1px solid #e0e0e0;
  gap: 16px;
`;

const SubNavbarInner = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
  width: 100%;
  max-width: 75rem;
  margin-left: auto;
  margin-right: auto;
`;

const StyledNavLink = styled(Link, {
  shouldForwardProp: (prop) => prop !== 'isActive',
})<{ isActive?: boolean }>`
  padding: 0 16px;
  font-size: 18px;
  color: ${(props) => (props.isActive ? '#a78bfa' : '#ffffff')};
  text-decoration: none !important;
  padding-bottom: 4px;
  display: inline-flex;
  align-items: center;
  transition: color 0.2s ease;

  &:hover {
    color: #a78bfa;
    text-decoration: none !important;
  }
`;

const StyledSubNavLink = styled(Link, {
  shouldForwardProp: (prop) => prop !== 'isActive',
})<{ isActive?: boolean }>`
  padding: 8px 16px;
  font-size: 16px;
  color: ${(props) => (props.isActive ? '#6e4ff9' : 'rgb(13, 0, 1)')};
  text-decoration: none !important;
  font-weight: normal;
  border-radius: 6px;
  background: transparent;
  transition: color 0.2s ease;

  &:hover {
    color: #6e4ff9;
    text-decoration: none !important;
  }
`;

const StyledJobsButton = styled('button', {
  shouldForwardProp: (prop) => prop !== 'isActive',
})<{ isActive?: boolean }>`
  padding: 8px 16px;
  font-size: 16px;
  color: ${(props) => (props.isActive ? '#6e4ff9' : 'rgb(13, 0, 1)')};
  background: transparent;
  border: none;
  cursor: pointer;
  border-radius: 6px;
  font-weight: normal;
  transition: color 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: inherit;

  &:hover {
    color: #6e4ff9;
  }
`;

const DropdownItemWrapper = styled.div`
  a {
    display: block;
    padding: 8px 16px;
    font-size: 14px;
    color: rgb(13, 0, 1);
    text-decoration: none !important;
    cursor: pointer;

    &:hover {
      color: #6e4ff9;
      background: #f5f7fa;
    }
  }
`;

export const TopNavigation = () => {
  const pathname = usePathname();
  const featureFlags = useContext(FeatureFlagsContext);
  const user = useContext(UserContext);
  const isReviewEnabled = featureFlags.includes(FEATURE_FLAG.REVIEW);

  // Dropdown states
  const jobsButtonRef = useRef<HTMLButtonElement | null>(null);
  const tomogramsButtonRef = useRef<HTMLButtonElement | null>(null);
  const dataButtonRef = useRef<HTMLButtonElement | null>(null);
  const [isJobsDropdownOpen, setIsJobsDropdownOpen] = useState(false);
  const [isTomogramsDropdownOpen, setIsTomogramsDropdownOpen] = useState(false);
  const [isDataDropdownOpen, setIsDataDropdownOpen] = useState(false);

  // Check if any Jobs route is active
  const isJobsActive = pathname.startsWith('/processing/jobs');

  // Check if any Tomograms route is active
  const isTomogramsActive = pathname.startsWith('/processing/tomograms');

  // Check if any Data route is active
  const isDataActive = pathname.startsWith('/processing/data');

  const handleLogout = () => {
    // Redirect to logout and then back to frontend home page
    const frontendUrl = window.location.origin;
    window.location.href = `${DJANGO_URL}/admin/logout/?next=${encodeURIComponent(frontendUrl)}`;
  };

  // Determine active section based on pathname
  const getActiveSection = (): NavSection => {
    if (pathname === '/') return 'home';
    if (pathname.startsWith('/samples')) return 'samples';
    if (pathname.startsWith('/sessions')) return 'sessions';
    if (pathname.startsWith('/processing')) return 'processing';
    return 'home';
  };

  const activeSection = getActiveSection();
  // Processing section uses dropdowns instead of flat sub-nav items
  const subNavItems = activeSection === 'processing' ? [] : SUB_NAV_ITEMS[activeSection];

  return (
    <StyledNav>
      {/* Main Navigation */}
      <StyledNavbar>
        <NavbarInner>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography
              variant="h4"
              component="span"
              sx={{
                color: '#6E4FF9',
                fontWeight: 700,
                fontSize: '32px',
                paddingRight: '5px',
              }}
            >
              [o]
            </Typography>
            <Link
              href="/"
              style={{
                textDecoration: 'none',
                color: '#ffffff',
              }}
            >
              <Typography
                variant="h4"
                component="h1"
                sx={{
                  color: '#ffffff',
                  fontWeight: 500,
                  fontSize: '24px',
                  paddingRight: '32px',
                  cursor: 'pointer',
                  '&:hover': {
                    opacity: 0.9,
                  },
                }}
              >
                Embrella
              </Typography>
            </Link>
            <Box
              className={'sds-font-body-xl'}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0,
                marginTop: '8px',
              }}
            >
              {MAIN_NAV_ITEMS.map((item) => {
                return (
                  <StyledNavLink key={item.section} href={item.href} isActive={activeSection === item.section}>
                    {item.label}
                  </StyledNavLink>
                );
              })}
            </Box>
          </Box>
          <Box>
            <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
              <Button
                sdsType="secondary"
                sdsStyle="square"
                size="small"
                onClick={() => (window.location.href = `${DJANGO_URL}/admin/`)}
                sx={{
                  color: '#ffffff !important',
                  borderColor: '#ffffff !important',
                  '&:hover': {
                    borderColor: '#a78bfa !important',
                    color: '#a78bfa !important',
                  },
                }}
              >
                Admin
              </Button>
              <Button
                sdsType="secondary"
                sdsStyle="square"
                size="small"
                onClick={() => window.open(`${DJANGO_URL}/docs/tutorials/userguide/`, '_blank')}
                sx={{
                  color: '#ffffff !important',
                  borderColor: '#ffffff !important',
                  '&:hover': {
                    borderColor: '#a78bfa !important',
                    color: '#a78bfa !important',
                  },
                }}
              >
                Docs
              </Button>
              <Button
                sdsType="secondary"
                sdsStyle="square"
                size="small"
                onClick={handleLogout}
                sx={{
                  color: '#ffffff !important',
                  borderColor: '#ffffff !important',
                  '&:hover': {
                    borderColor: '#a78bfa !important',
                    color: '#a78bfa !important',
                  },
                }}
              >
                Logout
              </Button>
            </Box>
            <Typography
              variant="caption"
              sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', color: '#ffffff' }}
            >
              {user?.username}
            </Typography>
          </Box>
        </NavbarInner>
      </StyledNavbar>

      {/* Sub Navigation */}
      {(activeSection === 'processing' || subNavItems.length > 0) && (
        <StyledSubNavbar>
          <SubNavbarInner>
            {/* Processing section dropdowns */}
            {activeSection === 'processing' && (
              <>
                {/* Jobs Dropdown */}
                <StyledJobsButton
                  ref={jobsButtonRef}
                  onClick={() => setIsJobsDropdownOpen((prev) => !prev)}
                  isActive={isJobsActive}
                >
                  Jobs
                  <Icon sdsIcon="ChevronDown" sdsSize="xs" />
                </StyledJobsButton>
                <DropdownMenu
                  label="Jobs"
                  options={JOBS_DROPDOWN_ITEMS.map((item) => ({
                    name: item.name,
                    component: (
                      <DropdownItemWrapper>
                        <Link href={item.href}>{item.label}</Link>
                      </DropdownItemWrapper>
                    ),
                  }))}
                  open={isJobsDropdownOpen}
                  onClickAway={() => setIsJobsDropdownOpen(false)}
                  anchorEl={jobsButtonRef.current}
                  PopperBaseProps={{
                    className: 'z-50 rounded-sds-m !w-[200px] [&_li]:list-none [&_svg]:hidden',
                    popperOptions: {
                      modifiers: [{ name: 'offset', options: { offset: [0, 4] } }],
                      placement: 'bottom-start',
                    },
                  }}
                />

                {/* Tomograms Dropdown */}
                <StyledJobsButton
                  ref={tomogramsButtonRef}
                  onClick={() => setIsTomogramsDropdownOpen((prev) => !prev)}
                  isActive={isTomogramsActive}
                >
                  Tomograms
                  <Icon sdsIcon="ChevronDown" sdsSize="xs" />
                </StyledJobsButton>
                <DropdownMenu
                  label="Tomograms"
                  options={getTomogramsDropdownItems(isReviewEnabled).map((item) => ({
                    name: item.name,
                    component: (
                      <DropdownItemWrapper>
                        <Link href={item.href}>{item.label}</Link>
                      </DropdownItemWrapper>
                    ),
                  }))}
                  open={isTomogramsDropdownOpen}
                  onClickAway={() => setIsTomogramsDropdownOpen(false)}
                  anchorEl={tomogramsButtonRef.current}
                  PopperBaseProps={{
                    className: 'z-50 rounded-sds-m !w-[200px] [&_li]:list-none [&_svg]:hidden',
                    popperOptions: {
                      modifiers: [{ name: 'offset', options: { offset: [0, 4] } }],
                      placement: 'bottom-start',
                    },
                  }}
                />

                {/* Data Dropdown */}
                <StyledJobsButton
                  ref={dataButtonRef}
                  onClick={() => setIsDataDropdownOpen((prev) => !prev)}
                  isActive={isDataActive}
                >
                  Data
                  <Icon sdsIcon="ChevronDown" sdsSize="xs" />
                </StyledJobsButton>
                <DropdownMenu
                  label="Data"
                  options={DATA_DROPDOWN_ITEMS.map((item) => ({
                    name: item.name,
                    component: (
                      <DropdownItemWrapper>
                        <Link href={item.href}>{item.label}</Link>
                      </DropdownItemWrapper>
                    ),
                  }))}
                  open={isDataDropdownOpen}
                  onClickAway={() => setIsDataDropdownOpen(false)}
                  anchorEl={dataButtonRef.current}
                  PopperBaseProps={{
                    className: 'z-50 rounded-sds-m !w-[200px] [&_li]:list-none [&_svg]:hidden',
                    popperOptions: {
                      modifiers: [{ name: 'offset', options: { offset: [0, 4] } }],
                      placement: 'bottom-start',
                    },
                  }}
                />
              </>
            )}
            {/* Other sub-nav items */}
            {subNavItems.map((item) => (
              <StyledSubNavLink key={item.href} href={item.href} isActive={pathname === item.href}>
                {item.label}
              </StyledSubNavLink>
            ))}
          </SubNavbarInner>
        </StyledSubNavbar>
      )}
    </StyledNav>
  );
};
