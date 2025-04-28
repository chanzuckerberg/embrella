import styled from "@emotion/styled";

export const ViewerContainer = styled.div`
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100%;
`;

export const TopBar = styled.div`
    display: flex;
    justify-content: space-between;
    align-items: center;
`;

export const Separator = styled.hr`
    width: 100%;
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 8px 0;
`;

export const MainContent = styled.div`
    display: flex;
    flex: 1;
    overflow: hidden;
`;

export const Sidebar = styled.div`
    display: flex;
    flex-direction: column;
    gap: 16px;
`;

export const SidebarSection = styled.div`
    display: flex;
    flex-direction: column;
    gap: 16px;
`;

export const TomogramTable = styled.div`
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    max-height: 300px;
    overflow-y: auto;
`;

export const TomogramTableHeader = styled.div`
    display: grid;
    grid-template-columns: 1fr 100px;
    padding: 8px;
    background: #f5f5f5;
    border-bottom: 1px solid #e0e0e0;
    position: sticky;
    top: 0;
    font-weight: 500;
`;

export const TomogramRow = styled.div<{ selected?: boolean }>`
    display: grid;
    grid-template-columns: 1fr 100px;
    padding: 8px;
    cursor: pointer;
    background: ${props => props.selected ? '#e6f3ff' : 'white'};
    border-bottom: 1px solid #e0e0e0;
    &:hover {
        background: ${props => props.selected ? '#e6f3ff' : '#f5f5f5'};
    }
    &:last-child {
        border-bottom: none;
    }
`;

export const NavigationButtons = styled.div`
    display: flex;
    gap: 8px;
`;

export const ViewControls = styled.div`
    display: flex;
    flex-direction: column;
    gap: 16px;
`;

export const Slider = styled.input`
    width: 100%;
`;

export const ViewerArea = styled.div`
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #f5f5f5;
    padding: 1rem;
`;

export const ZSliderContainer = styled.div`
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background-color: #fff;
    border-radius: 4px;
    margin-top: 1rem;
`;

export const QualityControls = styled.div`
    width: 300px;
    padding: 1rem;
    background-color: #fff;
    border-left: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    gap: 1rem;

    h3 {
        margin: 0;
    }
`;