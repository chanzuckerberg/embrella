import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'TEM Session List',
};

export default function TEMSessionsListLayout({ children }: { children: React.ReactNode }) {
  return children;
}
