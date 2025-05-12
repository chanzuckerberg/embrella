interface SideBarSectionProps {
  children: React.ReactNode;
}

export const SideBarSection = ({ children }: SideBarSectionProps) => {
  return <div className="flex flex-col gap-8">{children}</div>;
};
