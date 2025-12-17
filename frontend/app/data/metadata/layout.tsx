import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Metadata Visualization',
};

export default function DataMetadataLayout({ children }: { children: React.ReactNode }) {
  return children;
}
