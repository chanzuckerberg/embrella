import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sync Data',
};

export default function SyncLayout({ children }: { children: React.ReactNode }) {
  return children;
}
