import styled from "@emotion/styled";
import { gray300, spacesL, spacesS } from "@/app/common/theme";

export const StyledSidebar = styled.div`
  box-shadow: inset -0.5px 0 ${gray300};
  box-sizing: border-box;
  height: 100vh;
  width: 240px;
`;

export const StyledSidebarPositioner = styled.div`
  height: 100%;
  overflow: auto;
  padding: ${spacesL}px ${spacesS}px;
  width: 100%;
`;
