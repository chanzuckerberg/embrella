import styled from '@emotion/styled';
import { gray300, spacesS } from '@app/common/theme';

export const StyledFilters = styled.div`
  display: grid;
`;

export const FilterDivider = styled.hr`
  background: none;
  border: none;
  box-shadow: inset 0 -0.5px 0 ${gray300};
  height: 0.5px;
  margin: ${spacesS}px 0;
`;
