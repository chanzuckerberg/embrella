"use client";

import { useContext, useEffect, useState } from "react";
import styled from "@emotion/styled";
import { Link } from "@czi-sds/components";

import { spacesL, spacesS, spacesXxxs } from "@app/common/theme";
import {
  FEATURE_FLAG,
  FeatureFlagsContext,
} from "@app/common/context/FeatureFlagsProvider";

const TAB_PATHS_TO_LABELS: Record<string, string> = {
  cryo_grids: "Grids",
  tomograms: "Tomograms",
  annotations: "Annotations",
  reviews: "Reviews",
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
  const [baseNextUrl, setBaseNextUrl] = useState("");
  const [adminUrl, setAdminUrl] = useState("");
  const featureFlags = useContext(FeatureFlagsContext);
  const isReviewEnabled = featureFlags.includes(FEATURE_FLAG.REVIEW);

  useEffect(() => {
    setAdminUrl(getAdminUrl());
    setBaseNextUrl(getBaseNextUrl());
  }, []);

  return (
    <nav>
      <StyledNavbar>
        <span className={"sds-font-body-xl"}>
          <StyledNavLink href={adminUrl} fontWeight="bold">
            Startup Page
          </StyledNavLink>
          {Object.entries(TAB_PATHS_TO_LABELS).map(
            ([path, label]) =>
              (path !== "reviews" || isReviewEnabled) && (
                <StyledNavLink
                  key={path}
                  href={`${baseNextUrl}/${path}`}
                  fontWeight="bold"
                >
                  {label}
                </StyledNavLink>
              ),
          )}
        </span>
      </StyledNavbar>
    </nav>
  );
};

const getBaseUrl = (localhostPort: string): string => {
  if (typeof window === "undefined") {
    return "";
  }

  const { protocol, hostname } = window.location;
  let baseUrl = `${protocol}//${hostname}`;

  const isLocalhost = hostname === "localhost";
  if (isLocalhost) {
    baseUrl += `:${localhostPort}`;
  }

  return baseUrl;
};

const getAdminUrl = (): string => {
  const LOCALHOST_ADMIN_PORT = "8000";
  return getBaseUrl(LOCALHOST_ADMIN_PORT);
};

const getBaseNextUrl = (): string => {
  const LOCALHOST_NEXT_PORT = "3000";
  return `${getBaseUrl(LOCALHOST_NEXT_PORT)}/next`;
};
