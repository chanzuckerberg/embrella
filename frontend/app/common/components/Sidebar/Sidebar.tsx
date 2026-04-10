import React, { ReactNode, useContext, useState } from 'react';
import styled from '@emotion/styled';
import { Button } from '@mui/material';
import { Icon } from '@czi-sds/components';

import { gray100, spacesL, spacesS, spacesXs } from '@app/common/theme';
import {
  TableDispatchContext,
  TableStateActionTypes,
  TableStateContext,
} from '@app/common/components/TableStateProvider/TableStateProvider';

const EXPANDED_WIDTH = 210;
const COLLAPSED_WIDTH = 36;
const BORDER_COLOR = '#e0e0e0';

const StyledSidebar = styled.div`
  border: 1px solid ${BORDER_COLOR};
  border-radius: 4px;
  box-sizing: border-box;
  margin: ${spacesS}px 0 ${spacesS}px ${spacesS}px;
  max-height: calc(100vh - ${spacesS}px * 2);
  position: sticky;
  top: ${spacesS}px;
  transition: width 0.2s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  @media (max-width: 900px) {
    margin-left: 0;
    border-left: none;
    border-radius: 0 4px 4px 0;
  }
`;

const HeaderBar = styled.button`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: ${EXPANDED_WIDTH}px;
  min-height: 36px;
  padding: ${spacesXs}px ${spacesS}px;
  background: ${gray100};
  border: none;
  border-bottom: 1px solid ${BORDER_COLOR};
  cursor: pointer;
  flex-shrink: 0;
  box-sizing: border-box;

  &:hover {
    filter: brightness(0.97);
  }
`;

const HeaderLabel = styled.span`
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: inherit;
  white-space: nowrap;
`;

const StyledSidebarPositioner = styled.div`
  flex: 1;
  overflow: auto;
  padding: ${spacesL}px ${spacesS}px;
  width: ${EXPANDED_WIDTH}px;
`;

const ResetFooter = styled.div`
  flex-shrink: 0;
  background: ${gray100};
  border-top: 1px solid ${BORDER_COLOR};
  padding: ${spacesS}px;
  width: ${EXPANDED_WIDTH}px;
  box-sizing: border-box;
`;

const ResetButton = styled(Button)`
  text-transform: none;
  font-size: 12px;
  width: 100%;
  color: #1976d2;
`;

interface Props {
  children: ReactNode;
  className?: string;
}

export const Sidebar = ({ children, className }: Props): JSX.Element => {
  const [collapsed, setCollapsed] = useState(false);
  const state = useContext(TableStateContext);
  const dispatch = useContext(TableDispatchContext);
  const hasActiveFilters = Object.keys(state.filterState).length > 0;

  return (
    <StyledSidebar style={{ width: collapsed ? COLLAPSED_WIDTH : EXPANDED_WIDTH }} className={className}>
      <HeaderBar onClick={() => setCollapsed((prev) => !prev)} aria-label="Toggle filters">
        {!collapsed && <HeaderLabel>Filters</HeaderLabel>}
        <Icon sdsIcon={collapsed ? 'ChevronRight' : 'ChevronLeft'} sdsSize="xs" />
      </HeaderBar>
      {!collapsed && (
        <>
          <StyledSidebarPositioner>{children}</StyledSidebarPositioner>
          {hasActiveFilters && (
            <ResetFooter>
              <ResetButton
                variant="text"
                size="small"
                onClick={() => dispatch({ type: TableStateActionTypes.ClearAllFilters })}
              >
                Reset Filters
              </ResetButton>
            </ResetFooter>
          )}
        </>
      )}
    </StyledSidebar>
  );
};
