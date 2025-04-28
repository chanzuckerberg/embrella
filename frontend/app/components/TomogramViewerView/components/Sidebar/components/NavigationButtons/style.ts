import styled from "@emotion/styled";

export const NavigationButtonsContainer = styled.div`
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1rem;

  button {
    flex: 1;
    font-size: 14px;
    color: #0066FF;

    &:disabled {
      color: #9E9E9E;
    }

    svg {
      width: 16px;
      height: 16px;
    }
  }
`;