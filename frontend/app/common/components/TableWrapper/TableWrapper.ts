import styled from '@emotion/styled';
import { spacesS, spacesXl } from '@app/common/theme';

export const TableWrapper = styled.div`
  height: 100vh;
  overflow: auto;
  padding: ${spacesS}px ${spacesXl}px;

  @media (max-width: 900px) {
    padding-left: ${spacesS}px;
    padding-right: ${spacesS}px;
  }
`;
