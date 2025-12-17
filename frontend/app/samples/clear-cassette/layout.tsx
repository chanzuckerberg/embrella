import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Clear Cassette',
};

export default function ClearCassetteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
