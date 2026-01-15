import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Grid Boxes',
};

export default function GridBoxesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
