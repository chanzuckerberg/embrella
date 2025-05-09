interface SideBarSectionProps {
    children: React.ReactNode;
}

export const SideBarSection = ({ children }: SideBarSectionProps) => {
    return (
        <div className="p-4 border-b border-gray-300 last:border-b-0">
            {children}
        </div>
    );
};
