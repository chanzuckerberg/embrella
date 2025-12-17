import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Browse Sessions',
};

export default function BrowseSessionsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
