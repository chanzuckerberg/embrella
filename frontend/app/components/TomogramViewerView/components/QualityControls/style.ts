import styled from "@emotion/styled";

export const QualityControlsContainer = styled.div`
  width: 300px;
  padding: 1rem;
  background-color: #fff;
  border-left: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  gap: 1rem;

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }

  button {
    text-align: left;
    justify-content: flex-start;
    padding: 12px;
    font-size: 14px;
  }
`;