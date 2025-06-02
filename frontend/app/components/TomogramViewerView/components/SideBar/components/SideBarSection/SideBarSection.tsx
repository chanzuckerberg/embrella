import { PropsWithChildren } from 'react';

export interface SideBarSectionProps extends PropsWithChildren {
  className?: string;
}

export const SideBarSection = ({ children, className }: SideBarSectionProps) => {
  return <div className={`flex flex-col gap-[10px] border-gray-300 !p-[20px] ${className}`}>{children}</div>;
};
