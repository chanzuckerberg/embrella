import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'View Review',
};

export default function ReviewLayout({ children }: { children: React.ReactNode }) {
  return children;
}
