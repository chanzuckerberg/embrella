import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Cancel Jobs',
};

export default function CancelLayout({ children }: { children: React.ReactNode }) {
  return children;
}
