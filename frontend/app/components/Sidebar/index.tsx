import React from "react";
import {
  StyledSidebar,
  StyledSidebarPositioner,
} from "@/app/components/Sidebar/style";
import { Props } from "@/app/components/Sidebar/types";

export const Sidebar = ({ children, className }: Props): JSX.Element => {
  return (
    <StyledSidebar className={className}>
      <StyledSidebarPositioner>{children}</StyledSidebarPositioner>
    </StyledSidebar>
  );
};
