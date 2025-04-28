import styled from "@emotion/styled";

export const TomogramTableContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

export const TomogramTableHeader = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  font-weight: bold;
  padding: 0.5rem;
  background-color: #f5f5f5;
  border-radius: 4px;
`;

interface TomogramRowProps {
    selected: boolean;
}

export const TomogramRow = styled.div<TomogramRowProps>`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  padding: 0.5rem;
  cursor: pointer;
  background-color: ${({ selected }) => (selected ? '#e3f2fd' : 'transparent')};
  border-radius: 4px;

  &:hover {
    background-color: ${({ selected }) => (selected ? '#e3f2fd' : '#f5f5f5')};
  }
`;