import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'TEM Sessions',
};

export default function TEMSessionsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
