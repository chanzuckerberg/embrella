"use client";

import { useEffect, useState } from "react";
import styled from "@emotion/styled";
import { Link } from "@czi-sds/components";

import { spacesL, spacesS, spacesXxxs } from "@app/common/theme";

const TAB_PATHS_TO_LABELS: Record<string, string> = {
  cryo_grids: "Grids",
  tomograms: "Tomograms",
  annotations: "Annotations",
};

const StyledNavbar = styled.span`
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: ${spacesL}px ${spacesS}px;
  border-bottom: ${spacesXxxs}px solid;
  width: 100%;
`;

const StyledNavLink = styled(Link)`
  padding: 0 ${spacesL}px;
  font-size: 18px;
`;

export const TopNavigation = () => {
  const [adminUrl, setAdminUrl] = useState("");

  useEffect(() => {
    setAdminUrl(getAdminUrl());
  }, []);

  return (
    <nav>
      <StyledNavbar>
        <span className={"sds-font-body-xl"}>
          <StyledNavLink href={adminUrl} fontWeight="bold">
            Admin Page
          </StyledNavLink>
          {Object.entries(TAB_PATHS_TO_LABELS).map(([path, label]) => (
            <StyledNavLink key={path} href={path} fontWeight="bold">
              {label}
            </StyledNavLink>
          ))}
        </span>
      </StyledNavbar>
    </nav>
  );
};

const getAdminUrl = (): string => {
  if (typeof window === "undefined") {
    return "";
  }

  const { protocol, hostname } = window.location;
  const LOCALHOST_ADMIN_PORT = 8000;

  // Check if running on localhost
  const isLocalhost = hostname === "localhost";

  let adminUrl = `${protocol}//${hostname}`;
  if (isLocalhost) {
    adminUrl += `:${LOCALHOST_ADMIN_PORT}`;
  }

  // Remove the `/next` portion if it exists
  adminUrl = adminUrl.replace(/\/next$/, "");

  return adminUrl;
};
