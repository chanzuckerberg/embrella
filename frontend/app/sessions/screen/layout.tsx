import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Screen Grids',
};

export default function ScreenGridsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
