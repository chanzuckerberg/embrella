import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'New TEM Session',
};

export default function NewSessionLayout({ children }: { children: React.ReactNode }) {
  return children;
}
