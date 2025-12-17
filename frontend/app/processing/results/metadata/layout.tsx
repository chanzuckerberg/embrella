import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Metadata',
};

export default function MetadataLayout({ children }: { children: React.ReactNode }) {
  return children;
}
