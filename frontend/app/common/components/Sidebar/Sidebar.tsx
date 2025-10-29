import React, { ReactNode } from 'react';
import styled from '@emotion/styled';

import { gray300, spacesL, spacesS } from '@app/common/theme';

const StyledSidebar = styled.div`
  box-shadow: inset -0.5px 0 ${gray300};
  box-sizing: border-box;
  height: 100vh;
  width: 210px;
`;

const StyledSidebarPositioner = styled.div`
  height: 100%;
  overflow: auto;
  padding: ${spacesL}px ${spacesS}px;
  width: 100%;
`;

interface Props {
  children: ReactNode;
  className?: string;
}

export const Sidebar = ({ children, className }: Props): JSX.Element => {
  return (
    <StyledSidebar className={className}>
      <StyledSidebarPositioner>{children}</StyledSidebarPositioner>
    </StyledSidebar>
  );
};
