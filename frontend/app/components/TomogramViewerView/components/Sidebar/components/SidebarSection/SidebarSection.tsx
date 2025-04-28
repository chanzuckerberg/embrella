import { SidebarSectionContainer } from './style';

interface SidebarSectionProps {
    children: React.ReactNode;
}

export const SidebarSection = ({ children }: SidebarSectionProps) => {
    return <SidebarSectionContainer>{children}</SidebarSectionContainer>;
};